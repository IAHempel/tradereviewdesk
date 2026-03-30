import tempfile
import time
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

from fastapi.testclient import TestClient

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.core import auth as auth_module
from app.core.config import settings
from app.main import create_application
from app.schemas.billing import SubscriptionResponse
from app.schemas.reports import PremarketOutput
from app.services import state_store
from app.services.report_generation_provider import report_generation_provider


class TradeNocApiIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        temp_path = Path(self.temp_dir.name)
        seed_copy = temp_path / "seed_state.json"
        store_copy = temp_path / "store_state.json"
        seed_copy.write_text(state_store.SEED_PATH.read_text(encoding="utf-8"), encoding="utf-8")

        self.patches = [
            patch.object(settings, "auth_mode", "clerk"),
            patch.object(settings, "persistence_mode", "file"),
            patch.object(settings, "auth_internal_shared_secret", "test-shared-secret"),
            patch.object(settings, "auth_request_ttl_seconds", 300),
            patch.object(settings, "llm_api_key", "replace-me"),
            patch.object(settings, "stripe_webhook_secret", "whsec_test_signature"),
            patch.object(settings, "app_url", "http://testserver"),
            patch.object(settings, "app_env", "test"),
            patch.object(state_store, "DATA_DIR", temp_path),
            patch.object(state_store, "SEED_PATH", seed_copy),
            patch.object(state_store, "STORE_PATH", store_copy),
        ]

        for active_patch in self.patches:
            active_patch.start()

        state_store.reset_state_from_seed()
        self.client = TestClient(create_application())

    def tearDown(self) -> None:
        self.client.close()
        for active_patch in reversed(self.patches):
            active_patch.stop()
        self.temp_dir.cleanup()

    def auth_headers(
        self,
        *,
        user_id: str = "user-1",
        email: str = "user-1@example.com",
        display_name: str = "User One",
    ) -> dict[str, str]:
        timestamp = str(int(time.time()))
        signature = auth_module._build_signature(
            auth_provider="clerk",
            auth_user_id=user_id,
            auth_email=email,
            auth_display_name=display_name,
            auth_timestamp=timestamp,
        )
        return {
            "X-TradeNOC-Auth-Provider": "clerk",
            "X-TradeNOC-Auth-User-Id": user_id,
            "X-TradeNOC-Auth-Email": email,
            "X-TradeNOC-Auth-Display-Name": display_name,
            "X-TradeNOC-Auth-Timestamp": timestamp,
            "X-TradeNOC-Auth-Signature": signature,
        }

    def test_auth_requires_signed_headers(self) -> None:
        missing = self.client.get("/api/v1/profile")
        self.assertEqual(missing.status_code, 401)
        self.assertIn("Missing auth headers", missing.json()["detail"])

        invalid_headers = self.auth_headers()
        invalid_headers["X-TradeNOC-Auth-Signature"] = "bad-signature"
        invalid = self.client.get("/api/v1/profile", headers=invalid_headers)
        self.assertEqual(invalid.status_code, 401)
        self.assertEqual(invalid.json()["detail"], "Invalid auth signature.")

    def test_profile_and_trade_data_are_isolated_per_user(self) -> None:
        alpha_headers = self.auth_headers(user_id="alpha", email="alpha@example.com", display_name="Alpha")
        beta_headers = self.auth_headers(user_id="beta", email="beta@example.com", display_name="Beta")

        alpha_profile = self.client.put(
            "/api/v1/profile",
            headers=alpha_headers,
            json={"display_name": "Alpha Prime", "experience_level": "advanced"},
        )
        beta_profile = self.client.put(
            "/api/v1/profile",
            headers=beta_headers,
            json={"display_name": "Beta Prime", "experience_level": "beginner"},
        )
        self.assertEqual(alpha_profile.status_code, 200)
        self.assertEqual(beta_profile.status_code, 200)

        alpha_trade = self.client.post(
            "/api/v1/trades",
            headers=alpha_headers,
            json={
                "trade_date": "2026-03-30",
                "symbol": "NVDA",
                "asset_type": "stock",
                "side": "long",
                "quantity": 10,
                "entry_price": 120.5,
                "exit_price": 123.2,
                "pnl": 27.0,
                "fees": 1.0,
                "tags": ["earnings"],
                "notes": "Alpha-only trade",
                "source_type": "manual",
            },
        )
        self.assertEqual(alpha_trade.status_code, 200)

        alpha_trades = self.client.get("/api/v1/trades", headers=alpha_headers)
        beta_trades = self.client.get("/api/v1/trades", headers=beta_headers)
        self.assertEqual(alpha_trades.status_code, 200)
        self.assertEqual(beta_trades.status_code, 200)
        self.assertTrue(any(trade["symbol"] == "NVDA" for trade in alpha_trades.json()))
        self.assertFalse(any(trade["symbol"] == "NVDA" for trade in beta_trades.json()))

        self.assertEqual(self.client.get("/api/v1/profile", headers=alpha_headers).json()["display_name"], "Alpha Prime")
        self.assertEqual(self.client.get("/api/v1/profile", headers=beta_headers).json()["display_name"], "Beta Prime")

    def test_checklists_are_gated_for_free_and_work_for_paid_users(self) -> None:
        headers = self.auth_headers(user_id="free-checklist-user", email="free-checklist@example.com", display_name="Free Checklist")
        blocked = self.client.post(
            "/api/v1/checklist-templates",
            headers=headers,
            json={
                "name": "Opening Bell",
                "description": "Paid checklist",
                "is_default": True,
                "items": [
                    {
                        "id": "item-1",
                        "label": "Catalyst confirmed",
                        "description": "Know the reason for the move",
                        "is_required": True,
                        "display_order": 1,
                    }
                ],
            },
        )
        self.assertEqual(blocked.status_code, 402)

        pro_subscription = SubscriptionResponse(plan="pro", status="active", current_period_end=None, is_stub=True)
        with patch("app.services.billing_service.get_subscription", return_value=pro_subscription):
            created_template = self.client.post(
                "/api/v1/checklist-templates",
                headers=headers,
                json={
                    "name": "Opening Bell",
                    "description": "Paid checklist",
                    "is_default": True,
                    "items": [
                        {
                            "id": "item-1",
                            "label": "Catalyst confirmed",
                            "description": "Know the reason for the move",
                            "is_required": True,
                            "display_order": 1,
                        }
                    ],
                },
            )
            self.assertEqual(created_template.status_code, 200)
            template_id = created_template.json()["id"]

            created_run = self.client.post(
                "/api/v1/checklist-runs",
                headers=headers,
                json={
                    "template_id": template_id,
                    "session_date": "2026-03-30",
                    "symbol": "AAPL",
                    "setup_tag": "opening-range-breakout",
                    "reason_for_entry": "Checklist aligned before entry",
                    "confidence_score": 4,
                    "items": [{"label_snapshot": "Catalyst confirmed", "completed": True}],
                },
            )
            self.assertEqual(created_run.status_code, 200)
            self.assertEqual(created_run.json()["symbol"], "AAPL")

    def test_csv_import_persists_valid_rows_and_reports_invalid_rows(self) -> None:
        headers = self.auth_headers()
        csv_payload = "\n".join(
            [
                "date,symbol,side,qty,entry_price,exit_price,pnl,fees,tags,notes",
                "2026-03-28,AAPL,buy,10,190.5,192.2,17.0,1.25,opening|momentum,Valid row one",
                "2026-03-28,,buy,5,120.0,121.0,5.0,1.00,,Missing symbol row",
                "2026-03-29,TSLA,sell,2,170.0,168.0,4.0,1.00,fade,Valid row two",
            ]
        )
        response = self.client.post(
            "/api/v1/trades/upload-csv",
            headers=headers,
            files={"file": ("trades.csv", csv_payload.encode("utf-8"), "text/csv")},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["rows_received"], 3)
        self.assertEqual(body["imported_count"], 2)
        self.assertEqual(body["rejected_count"], 1)
        self.assertEqual(body["errors"][0]["message"], "Missing symbol.")

        trades = self.client.get("/api/v1/trades", headers=headers)
        self.assertEqual(trades.status_code, 200)
        symbols = [trade["symbol"] for trade in trades.json()]
        self.assertIn("AAPL", symbols)
        self.assertIn("TSLA", symbols)

    def test_report_generation_covers_success_and_failure_paths(self) -> None:
        headers = self.auth_headers()
        premarket = self.client.post(
            "/api/v1/reports/premarket/generate",
            headers=headers,
            json={
                "report_date": "2026-03-30",
                "user_profile": {"experience_level": "intermediate"},
                "watchlist_symbols": ["AAPL", "NVDA"],
                "prior_notes": ["Respect opening volatility"],
                "manual_events": ["CPI tomorrow"],
                "user_priorities": ["Stay selective"],
            },
        )
        self.assertEqual(premarket.status_code, 200)
        self.assertEqual(premarket.json()["job"]["status"], "succeeded")
        self.assertEqual(premarket.json()["report"]["report_type"], "premarket")

        pro_subscription = SubscriptionResponse(plan="pro", status="active", current_period_end=None, is_stub=True)
        with patch("app.services.billing_service.get_subscription", return_value=pro_subscription):
            debrief = self.client.post(
                "/api/v1/reports/debrief/generate",
                headers=headers,
                json={
                    "report_date": "2026-03-30",
                    "user_profile": {"experience_level": "intermediate"},
                    "trade_entries": [],
                    "checklist_runs": [],
                    "user_notes": ["Stayed process-first"],
                },
            )
            self.assertEqual(debrief.status_code, 200)
            self.assertEqual(debrief.json()["job"]["status"], "succeeded")

            weekly_failure = self.client.post(
                "/api/v1/reports/weekly-review/generate",
                headers=headers,
                json={
                    "week_start": "2026-03-23",
                    "week_end": "2026-03-27",
                    "user_profile": {"experience_level": "intermediate"},
                    "debrief_summaries": ["[force-fail] trigger failed validation"],
                    "trade_entries": [],
                    "checklist_run_summaries": [],
                },
            )
            self.assertEqual(weekly_failure.status_code, 200)
            self.assertEqual(weekly_failure.json()["job"]["status"], "failed")
            self.assertIsNone(weekly_failure.json()["report"])

    def test_report_generation_uses_openai_provider_when_key_is_configured(self) -> None:
        headers = self.auth_headers(user_id="openai-user", email="openai-user@example.com", display_name="OpenAI User")

        class FakeResponse:
            def __init__(self) -> None:
                self.output_text = PremarketOutput(
                    summary="AI-generated summary",
                    watchlist_priorities=[{"symbol": "MSFT", "priority": "high", "reason": "Relative strength"}],
                    changes_to_watch=["Fed speakers"],
                    focus_reminders=["Stay selective."],
                    session_checklist=["Write the plan first."],
                    disclaimer="Workflow support only. No trade recommendations or execution guidance.",
                ).model_dump_json()
                self.usage = None

        with patch.object(settings, "llm_api_key", "sk-live-test"), patch.object(report_generation_provider, "_client", None):
            with patch.object(report_generation_provider, "_get_client") as mock_get_client, patch.object(
                report_generation_provider,
                "_build_usage_metrics",
                return_value={
                    "provider": "openai",
                    "model": "gpt-4.1-mini",
                    "input_tokens": 120,
                    "output_tokens": 80,
                    "total_tokens": 200,
                    "estimated_cost_usd": 0.000176,
                },
            ):
                mock_get_client.return_value.responses.create.return_value = FakeResponse()

                response = self.client.post(
                    "/api/v1/reports/premarket/generate",
                    headers=headers,
                    json={
                        "report_date": "2026-03-30",
                        "user_profile": {"experience_level": "intermediate"},
                        "watchlist_symbols": ["MSFT"],
                        "prior_notes": [],
                        "manual_events": ["Fed speakers"],
                        "user_priorities": ["Wait for clean entries"],
                    },
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["job"]["status"], "succeeded")
        self.assertEqual(response.json()["report"]["parsed_output"]["summary"], "AI-generated summary")
        self.assertEqual(response.json()["job"]["usage_metrics"]["provider"], "openai")
        self.assertEqual(response.json()["job"]["usage_metrics"]["total_tokens"], 200)

    def test_billing_endpoints_cover_stub_checkout_and_signature_validation(self) -> None:
        unique_suffix = str(int(time.time() * 1000))
        headers = self.auth_headers(
            user_id=f"billing-user-{unique_suffix}",
            email=f"billing-user-{unique_suffix}@example.com",
            display_name="Billing User",
        )
        subscription = self.client.get("/api/v1/billing/subscription", headers=headers)
        self.assertEqual(subscription.status_code, 200)
        self.assertEqual(subscription.json()["plan"], "free")
        self.assertTrue(subscription.json()["is_stub"])

        checkout = self.client.post(
            "/api/v1/billing/create-checkout-session",
            headers=headers,
            json={"plan": "pro"},
        )
        self.assertEqual(checkout.status_code, 200)
        self.assertEqual(checkout.json()["mode"], "stub")
        self.assertIn("stub-checkout", checkout.json()["url"])

        webhook = self.client.post(
            "/api/v1/billing/webhooks/stripe",
            headers={"Stripe-Signature": "t=123,v1=bad"},
            content=b'{"type":"checkout.session.completed","data":{"object":{"metadata":{"auth_provider_id":"clerk:user-1","email":"user-1@example.com","plan":"pro"}}}}',
        )
        self.assertEqual(webhook.status_code, 400)
        self.assertEqual(webhook.json()["detail"], "Invalid Stripe signature.")


if __name__ == "__main__":
    unittest.main()
