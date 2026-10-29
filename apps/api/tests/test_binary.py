import math
import random
import sys
import tempfile
import time
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.core import auth as auth_module
from app.core.config import settings
from app.main import create_application
from app.schemas.binary import BinaryConfig
from app.services import state_store
from app.services.binary import engine
from app.services.binary.engine import probability_up, run_binary
from app.services.desk.market import MarketDataError

NOW = datetime(2026, 10, 28, 20, 7, tzinfo=UTC)


class FakeCoinbase:
    """Serves /products/{id}/candles like Coinbase: newest first, at most 300 rows, some minutes missing."""

    def __init__(self, *, coverage: float = 0.97) -> None:
        self.coverage = coverage
        self.requests: list[httpx.Request] = []
        self.status: int | None = None

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.status:
            return httpx.Response(self.status, json={"message": "slow down"})
        product = request.url.path.split("/")[2]
        start = datetime.fromisoformat(request.url.params["start"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(request.url.params["end"].replace("Z", "+00:00"))
        rng = random.Random(f"{product}-{start.isoformat()}")
        price = 60_000.0 if product.startswith("BTC") else 3_000.0
        rows = []
        moment = start
        while moment <= end and len(rows) < 300:
            open_ = price
            price *= math.exp(rng.gauss(0, 0.0008))
            if rng.random() < self.coverage:
                rows.append([int(moment.timestamp()), min(open_, price) * 0.9997, max(open_, price) * 1.0003, open_, price, rng.random() * 5])
            moment += timedelta(minutes=1)
        return httpx.Response(200, json=list(reversed(rows)))

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handler))


def run(**overrides):
    return run_binary(BinaryConfig(**{"seed": 5, "hours": 2, **overrides}), now=NOW)


class BinaryMathTests(unittest.TestCase):
    def test_probability_up(self) -> None:
        self.assertAlmostEqual(probability_up(100, 100, 0.001, 10), 0.5)
        self.assertGreater(probability_up(100.2, 100, 0.001, 10), 0.5)
        self.assertLess(probability_up(99.8, 100, 0.001, 10), 0.5)
        self.assertGreater(probability_up(100.2, 100, 0.001, 1), probability_up(100.2, 100, 0.001, 10))
        self.assertEqual(probability_up(100.0, 100, 0.001, 0), 1.0)
        self.assertEqual(probability_up(99.9, 100, 0.001, 0), 0.0)

    def test_end_snaps_to_the_last_completed_window(self) -> None:
        resolved = engine.resolve_config(BinaryConfig(seed=1), NOW)
        self.assertEqual(resolved.end_at, datetime(2026, 10, 28, 20, 0, tzinfo=UTC))


class BinarySimulationTests(unittest.TestCase):
    def test_deterministic(self) -> None:
        self.assertEqual(run().model_dump_json(), run().model_dump_json())
        self.assertNotEqual(run().model_dump_json(), run(seed=6).model_dump_json())

    def test_window_accounting_balances(self) -> None:
        result = run(assets=["BTC", "ETH"])
        self.assertEqual(len(result.minutes), 120)
        self.assertEqual(len(result.windows), 2 * 8)
        for window in result.windows:
            payout = window.up_shares if window.outcome == "up" else window.down_shares
            self.assertAlmostEqual(window.pnl, payout - window.up_cost - window.down_cost - window.fees, places=3)
            self.assertEqual(window.pairs, min(window.up_shares, window.down_shares))
            self.assertLessEqual(window.up_shares, result.config.max_shares_per_side)
            self.assertLessEqual(window.down_shares, result.config.max_shares_per_side)
        self.assertAlmostEqual(result.summary.net_pnl, sum(window.pnl for window in result.windows), places=1)
        self.assertAlmostEqual(result.minutes[-1].equity, result.summary.ending_balance, places=1)
        self.assertEqual(sum(result.fill_arrival), result.summary.fills)

    def test_quotes_use_only_the_current_price_and_stop_before_the_close(self) -> None:
        result = run(stop_quoting_minutes=3, inventory_skew_cents=0)
        series = result.series[0]
        half_spread = result.config.half_spread_cents / 100
        for window_start in range(0, 120, 15):
            self.assertEqual(series.bid_up[window_start], round(series.fair_up[window_start] - half_spread, 3))
            self.assertEqual(series.bid_down[window_start], round(1 - series.fair_up[window_start] - half_spread, 3))
            for minute in range(window_start + 12, window_start + 15):
                self.assertIsNone(series.bid_up[minute])
                self.assertIsNone(series.bid_down[minute])

    def test_each_minutes_quotes_lock_in_less_than_a_dollar(self) -> None:
        # Pairs filled in different minutes can still cost more than $1 when fair value moves between fills;
        # the guarantee is per quote: both top bids posted together sum to $1 minus twice the half spread.
        result = run(inventory_skew_cents=0, hours=4)
        target = 1 - 2 * result.config.half_spread_cents / 100
        checked = 0
        for series in result.series:
            for fair, up, down in zip(series.fair_up, series.bid_up, series.bid_down, strict=True):
                if up is not None and down is not None and 0.05 < fair < 0.95:
                    self.assertAlmostEqual(up + down, target, delta=0.0015)
                    checked += 1
        self.assertGreater(checked, 100)

    def test_without_skew_no_bid_is_above_fair_value(self) -> None:
        result = run(inventory_skew_cents=0, hours=6, assets=["BTC", "ETH", "SOL", "XRP", "DOGE"])
        fair = {series.asset: series.fair_up for series in result.series}
        self.assertTrue(result.fills)
        for fill in result.fills:
            value = fair[fill.asset][fill.minute] if fill.side == "up" else 1 - fair[fill.asset][fill.minute]
            self.assertLessEqual(fill.price, value + 0.001)
            self.assertGreaterEqual(fill.price, 0.01)

    def test_baseline_is_the_same_rules_against_an_efficient_crowd(self) -> None:
        result = run(hours=4)
        self.assertNotEqual(result.baseline.net_pnl, result.summary.net_pnl)
        efficient = run(hours=4, crowd_lag_minutes=0, crowd_noise_cents=0)
        self.assertAlmostEqual(efficient.summary.net_pnl, efficient.baseline.net_pnl, places=2)

    def test_queue_probability_scales_fills(self) -> None:
        self.assertLess(run(queue_fill_probability=0.1).summary.fills, run(queue_fill_probability=0.9).summary.fills)


class CoinbaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache = patch.object(settings, "market_data_cache_dir", self.temp_dir.name)
        self.cache.start()

    def tearDown(self) -> None:
        self.cache.stop()
        self.temp_dir.cleanup()

    def test_pages_fills_gaps_and_caches(self) -> None:
        fake = FakeCoinbase()
        config = BinaryConfig(seed=2, hours=6, assets=["BTC"], data_source="coinbase")
        with fake.client() as client:
            first = run_binary(config, client=client, now=NOW)
            requests = len(fake.requests)
            second = run_binary(config, client=client, now=NOW)

        self.assertEqual(requests, 2)
        self.assertEqual(len(fake.requests), 2)
        params = fake.requests[0].url.params
        self.assertEqual(fake.requests[0].url.path, "/products/BTC-USD/candles")
        self.assertEqual(params["granularity"], "60")
        self.assertEqual(params["start"], "2026-10-28T13:00:00Z")
        self.assertEqual(len(first.series[0].price), 360)
        self.assertEqual(first.model_dump_json(), second.model_dump_json())

    def test_errors(self) -> None:
        fake = FakeCoinbase(coverage=0.5)
        with fake.client() as client, self.assertRaises(MarketDataError) as caught:
            run_binary(BinaryConfig(seed=2, assets=["BTC"], data_source="coinbase"), client=client, now=NOW)
        self.assertEqual(caught.exception.status_code, 422)

        fake = FakeCoinbase()
        fake.status = 429
        with fake.client() as client, self.assertRaises(MarketDataError) as caught:
            run_binary(BinaryConfig(seed=2, assets=["BTC", "ETH"], data_source="coinbase"), client=client, now=NOW)
        self.assertEqual(caught.exception.status_code, 429)

        with self.assertRaises(MarketDataError) as caught:
            run_binary(BinaryConfig(seed=2, data_source="coinbase", end_at=NOW + timedelta(hours=2)), now=NOW)
        self.assertEqual(caught.exception.status_code, 422)


class BinaryApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        temp_path = Path(self.temp_dir.name)
        seed_copy = temp_path / "seed_state.json"
        seed_copy.write_text(state_store.SEED_PATH.read_text(encoding="utf-8"), encoding="utf-8")
        self.patches = [
            patch.object(settings, "auth_mode", "clerk"),
            patch.object(settings, "persistence_mode", "file"),
            patch.object(settings, "auth_internal_shared_secret", "test-shared-secret"),
            patch.object(settings, "app_env", "test"),
            patch.object(state_store, "DATA_DIR", temp_path),
            patch.object(state_store, "SEED_PATH", seed_copy),
            patch.object(state_store, "STORE_PATH", temp_path / "store_state.json"),
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

    def headers(self, user_id: str = "binary-user") -> dict[str, str]:
        timestamp = str(int(time.time()))
        email = f"{user_id}@example.com"
        signature = auth_module._build_signature(
            auth_provider="clerk", auth_user_id=user_id, auth_email=email, auth_display_name="B", auth_timestamp=timestamp
        )
        return {
            "X-TradeNOC-Auth-Provider": "clerk",
            "X-TradeNOC-Auth-User-Id": user_id,
            "X-TradeNOC-Auth-Email": email,
            "X-TradeNOC-Auth-Display-Name": "B",
            "X-TradeNOC-Auth-Timestamp": timestamp,
            "X-TradeNOC-Auth-Signature": signature,
        }

    def test_runs_are_saved_scoped_and_validated(self) -> None:
        created = self.client.post("/api/v1/binary/runs", headers=self.headers(), json={"seed": 3, "hours": 1})
        self.assertEqual(created.status_code, 200, created.text)
        body = created.json()
        self.assertEqual(body["data_source"], "synthetic")
        self.assertIn("efficient", body["disclaimer"])
        listed = self.client.get("/api/v1/binary/runs", headers=self.headers()).json()
        self.assertEqual(listed[0]["id"], body["id"])
        self.assertIn("baseline", listed[0])
        self.assertNotIn("minutes", listed[0])
        self.assertEqual(self.client.get(f"/api/v1/binary/runs/{body['id']}", headers=self.headers()).json()["summary"], body["summary"])
        self.assertEqual(self.client.get(f"/api/v1/binary/runs/{body['id']}", headers=self.headers("other")).status_code, 404)
        self.assertEqual(self.client.post("/api/v1/binary/runs", headers=self.headers(), json={"hours": 99}).status_code, 422)
        self.assertEqual(self.client.get("/api/v1/binary/defaults", headers=self.headers()).json()["assets"], ["BTC", "ETH", "SOL"])


if __name__ == "__main__":
    unittest.main()
