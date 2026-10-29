import sys
import tempfile
import time
import unittest
from datetime import date, datetime
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
from app.schemas.desk import DeskConfig
from app.services import desk_live_service, state_store
from app.services.desk import live, notify
from app.services.desk.calendar import MARKET_TIMEZONE
from app.services.desk.engine import CheckpointDecision, CheckpointPolicy, DeskSession
from app.services.desk.market import MarketDataError, SimulatedMarketFeed
from market_fakes import FakeAlpaca

SYMBOLS = ["AAPL", "NVDA", "SPY", "QQQ"]
DAY = date(2025, 11, 26)


def at(hour: int, minute: int, second: int = 0, day: date = DAY) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, second, tzinfo=MARKET_TIMEZONE)


def synthetic(policy: CheckpointPolicy | None, seed: int):
    config = DeskConfig(symbols=SYMBOLS, seed=seed, sessions=1, max_daily_loss_pct=10)
    return DeskSession(config, {}, SimulatedMarketFeed(SYMBOLS, seed, 1), policy).run()


def first_seed_with_milestone(milestone: float) -> tuple[int, int]:
    """A seed whose synthetic day crosses `milestone` with bars left afterwards, and the step it happens."""
    for seed in range(200):
        result = synthetic(CheckpointPolicy(milestones=[milestone], drawdown_pct=10), seed)
        if result.checkpoints and result.checkpoints[0].step < 50:
            return seed, result.checkpoints[0].step
    raise AssertionError("no seed crossed the milestone")


class CheckpointEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.seed, cls.trigger = first_seed_with_milestone(1.002)

    def orders_after(self, result, step: int) -> list:
        return [event for event in result.events if event.kind == "order" and event.step >= step]

    def test_an_undecided_checkpoint_pauses_new_entries(self) -> None:
        result = synthetic(CheckpointPolicy(milestones=[1.002], drawdown_pct=10), self.seed)
        checkpoint = result.checkpoints[0]
        self.assertEqual((checkpoint.kind, checkpoint.decision), ("milestone", None))
        self.assertGreaterEqual(checkpoint.multiple, 1.002)
        self.assertEqual(self.orders_after(result, checkpoint.step), [])
        self.assertTrue(any(reason.code == "checkpoint_pause" for reason in result.kill_reasons))

    def test_continue_resumes_from_the_next_bar(self) -> None:
        decided = self.trigger + 3
        result = synthetic(
            CheckpointPolicy(milestones=[1.002], drawdown_pct=10, decisions={0: CheckpointDecision("continue", decided)}),
            self.seed,
        )
        checkpoint = result.checkpoints[0]
        self.assertEqual((checkpoint.decision, checkpoint.decided_step), ("continue", decided))
        resume = next(event for event in result.events if event.kind == "resume")
        self.assertEqual(resume.step, decided + 1)
        self.assertEqual([event for event in result.events if event.kind == "order" and checkpoint.step <= event.step <= decided], [])

    def test_stop_flattens_at_the_next_open_and_ends_entries(self) -> None:
        decided = self.trigger + 1
        result = synthetic(
            CheckpointPolicy(milestones=[1.002], drawdown_pct=10, decisions={0: CheckpointDecision("stop", decided)}),
            self.seed,
        )
        self.assertEqual(result.checkpoints[0].decision, "stop")
        self.assertEqual(self.orders_after(result, self.trigger), [])
        for frame in result.frames[decided + 1 :]:
            self.assertEqual(frame.positions, [])
        stopped = [trade for trade in result.trades if trade.exit_reason == "stopped"]
        self.assertTrue(all(trade.close_step == decided + 1 for trade in stopped))

    def test_manual_stop_without_a_checkpoint(self) -> None:
        result = synthetic(CheckpointPolicy(milestones=[5.0], drawdown_pct=10, manual_stop_step=20), 3)
        self.assertEqual(result.checkpoints, [])
        self.assertEqual(self.orders_after(result, 21), [])
        self.assertEqual(next(event for event in result.events if event.kind == "stopped").step, 21)

    def test_drawdown_checkpoint(self) -> None:
        for seed in range(100):
            result = synthetic(CheckpointPolicy(milestones=[5.0], drawdown_pct=0.25), seed)
            if result.checkpoints:
                checkpoint = result.checkpoints[0]
                self.assertEqual(checkpoint.kind, "drawdown")
                self.assertLessEqual(checkpoint.equity, 500 * (1 - 0.0025) + 0.01)
                return
        self.fail("no seed hit the drawdown checkpoint")


class NotifyTests(unittest.TestCase):
    def test_only_known_webhook_hosts(self) -> None:
        self.assertEqual(notify.channel_for("https://ntfy.sh/my-desk"), "ntfy")
        self.assertEqual(notify.channel_for("https://discord.com/api/webhooks/1/abc"), "discord")
        self.assertEqual(notify.channel_for("https://hooks.slack.com/services/T/B/x"), "slack")
        for bad in (
            "http://ntfy.sh/my-desk",
            "https://ntfy.sh/",
            "https://ntfy.sh/a/b",
            "https://user:pw@ntfy.sh/x",
            "https://ntfy.sh:8443/x",
            "https://discord.com/channels/1",
            "https://hooks.slack.com/other",
            "https://169.254.169.254/latest",
            "https://example.com/hook",
        ):
            with self.subTest(url=bad), self.assertRaises(notify.NotifyURLError):
                notify.channel_for(bad)
        with patch.object(settings, "desk_notify_extra_hosts", "ntfy.example.org"):
            self.assertEqual(notify.channel_for("https://ntfy.example.org/desk"), "ntfy")

    def test_payload_per_channel_and_failures_are_returned_not_raised(self) -> None:
        sent: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            sent.append(request)
            return httpx.Response(500 if "fail" in request.url.path else 200)

        message = notify.DeskNotification("Paper desk up 1%", "Keep running?", urgent=True)
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            self.assertIsNone(notify.send("https://ntfy.sh/desk", message, client=client))
            self.assertIsNone(notify.send("https://discord.com/api/webhooks/1/x", message, client=client))
            self.assertIsNone(notify.send("https://hooks.slack.com/services/T/B/x", message, client=client))
            self.assertIn("HTTP 500", notify.send("https://ntfy.sh/fail", message, client=client))
        self.assertEqual(sent[0].headers["Title"], "Paper desk up 1%")
        self.assertEqual(sent[0].headers["Priority"], "high")
        self.assertEqual(sent[0].content, b"Keep running?")
        self.assertIn("Keep running?", sent[1].read().decode())
        self.assertIn("Keep running?", sent[2].read().decode())


class LiveSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.patches = [
            patch.object(settings, "alpaca_api_key_id", "test-alpaca-id"),
            patch.object(settings, "alpaca_api_secret_key", "test-alpaca-secret"),
            patch.object(settings, "market_data_cache_dir", self.temp_dir.name),
        ]
        for active_patch in self.patches:
            active_patch.start()
        self.fake = FakeAlpaca()
        self.notifications: list[httpx.Request] = []

    def tearDown(self) -> None:
        for active_patch in reversed(self.patches):
            active_patch.stop()
        self.temp_dir.cleanup()

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.url.host == "ntfy.sh":
            self.notifications.append(request)
            return httpx.Response(200)
        return self.fake.handler(request)

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handler))

    def record(self, **config):
        return live.new_record(
            session_id="live-1",
            created_at=at(9, 0).isoformat(),
            config=DeskConfig(**{"symbols": SYMBOLS, "seed": 4, "data_source": "alpaca", "end_date": DAY, **config}),
            day=DAY,
            notify_url="https://ntfy.sh/desk-test",
            journal={},
        )

    def test_bar_math(self) -> None:
        self.assertEqual(live.completed_slots(DAY, at(9, 35, 10)), 0)
        self.assertEqual(live.completed_slots(DAY, at(9, 35, 20)), 1)
        self.assertEqual(live.completed_slots(DAY, at(16, 5)), 78)
        self.assertEqual(live.completed_slots(date(2025, 11, 28), at(13, 5, day=date(2025, 11, 28))), 42)
        self.assertEqual(live.next_bar_at(DAY, at(11, 2)), at(11, 5, 15))
        self.assertIsNone(live.next_bar_at(DAY, at(16, 1)))

    def test_start_rules(self) -> None:
        with self.assertRaises(MarketDataError) as caught:
            live.check_can_start(at(11, 0, day=date(2025, 11, 29)))
        self.assertEqual(caught.exception.status_code, 422)
        with self.assertRaises(MarketDataError):
            live.check_can_start(at(16, 0))
        self.assertEqual(live.check_can_start(at(8, 0)), DAY)
        with patch.object(settings, "alpaca_api_key_id", "replace-me"), self.assertRaises(MarketDataError) as caught:
            live.check_can_start(at(11, 0))
        self.assertEqual(caught.exception.status_code, 503)

    def test_waits_for_the_open_then_runs_on_completed_bars(self) -> None:
        with self.client() as client:
            early = live.tick(self.record(), now=at(9, 10), client=client)
            self.assertEqual(early.status, "scheduled")
            self.assertEqual(self.fake.requests, [])

            running = live.tick(early, now=at(11, 0), client=client)
        self.assertEqual(running.status, "running")
        result = running.result
        assert result is not None
        self.assertEqual(len(result.frames), 17)
        self.assertEqual(result.frames[-1].clock, "10:55")
        self.assertEqual(result.session_lengths, [78])
        self.assertEqual(result.session_labels, ["2025-11-26"])
        self.assertEqual(result.flow_source, "trade prints")
        paths = [request.url.path for request in self.fake.requests]
        self.assertEqual(paths, ["/v2/stocks/bars", "/v2/stocks/bars", "/v2/stocks/trades"])
        self.assertTrue(all(request.url.params["feed"] == "iex" for request in self.fake.requests))

    def test_new_bars_never_rewrite_earlier_ones(self) -> None:
        with self.client() as client:
            first = live.tick(self.record(), now=at(11, 0), client=client)
            later = live.tick(first, now=at(12, 30, 30), client=client)
        assert first.result is not None and later.result is not None
        self.assertEqual(len(later.result.frames), 36)
        self.assertEqual(
            [frame.model_dump() for frame in later.result.frames[:16]],
            [frame.model_dump() for frame in first.result.frames[:16]],
        )
        flow_requests = [request for request in self.fake.requests if request.url.path == "/v2/stocks/trades"]
        self.assertEqual(flow_requests[1].url.params["start"], "2025-11-26T15:55:00Z")

    def test_unchanged_minute_does_not_refetch(self) -> None:
        with self.client() as client:
            first = live.tick(self.record(), now=at(11, 0), client=client)
            count = len(self.fake.requests)
            same = live.tick(first, now=at(11, 0, 10), client=client)
        self.assertIs(same, first)
        self.assertEqual(len(self.fake.requests), count)

    def test_checkpoint_notifies_once_and_closes_with_a_summary(self) -> None:
        with self.client() as client:
            record = live.tick(self.record(milestones=[1.0001], checkpoint_drawdown_pct=0.25), now=at(10, 0), client=client)
            for hour, minute in ((11, 0), (12, 0), (13, 0), (14, 0), (15, 0), (16, 1)):
                if record.status == "awaiting_decision":
                    checkpoint = live.open_checkpoint(record)
                    assert checkpoint is not None
                    record = live.decide(record, checkpoint.index, "continue")
                    self.assertIsNone(live.open_checkpoint(record))
                    self.assertEqual(record.status, "running")
                record = live.tick(record, now=at(hour, minute), client=client)

        self.assertEqual(record.status, "closed")
        assert record.result is not None
        self.assertEqual(len(record.result.frames), 78)
        titles = [request.headers["Title"] for request in self.notifications]
        checkpoints = record.result.checkpoints
        self.assertEqual(len([title for title in titles if title.startswith("Paper desk")]), len(checkpoints))
        self.assertEqual(sum(title.startswith("Paper session closed") for title in titles), 1)
        self.assertTrue(all(checkpoint.decision == "continue" for checkpoint in checkpoints))

    def test_stop_waits_for_the_next_bar_then_is_final(self) -> None:
        with self.client() as client:
            record = live.tick(self.record(), now=at(11, 0), client=client)
            stopping = live.stop(record)
            self.assertIn(stopping.status, ("stopping", "stopped"))
            done = live.tick(stopping, now=at(11, 5, 30), client=client)
        self.assertEqual(done.status, "stopped")
        assert done.result is not None
        self.assertEqual(done.result.frames[-1].positions, [])
        self.assertTrue(any(event.kind == "stopped" for event in done.result.events))
        self.assertEqual(live.tick(done, now=at(12, 0), client=client), done)


class LiveApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        temp_path = Path(self.temp_dir.name)
        seed_copy = temp_path / "seed_state.json"
        seed_copy.write_text(state_store.SEED_PATH.read_text(encoding="utf-8"), encoding="utf-8")
        self.fake = FakeAlpaca()
        self.now = at(11, 0)
        self.patches = [
            patch.object(settings, "auth_mode", "clerk"),
            patch.object(settings, "persistence_mode", "file"),
            patch.object(settings, "auth_internal_shared_secret", "test-shared-secret"),
            patch.object(settings, "app_env", "test"),
            patch.object(settings, "alpaca_api_key_id", "test-alpaca-id"),
            patch.object(settings, "alpaca_api_secret_key", "test-alpaca-secret"),
            patch.object(settings, "market_data_cache_dir", self.temp_dir.name),
            patch.object(state_store, "DATA_DIR", temp_path),
            patch.object(state_store, "SEED_PATH", seed_copy),
            patch.object(state_store, "STORE_PATH", temp_path / "store_state.json"),
            patch.object(live, "_http_client", self.fake.client),
            patch.object(live, "live_now", lambda: self.now),
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

    def headers(self, user_id: str = "live-user") -> dict[str, str]:
        timestamp = str(int(time.time()))
        email = f"{user_id}@example.com"
        signature = auth_module._build_signature(
            auth_provider="clerk", auth_user_id=user_id, auth_email=email, auth_display_name="Live", auth_timestamp=timestamp
        )
        return {
            "X-TradeNOC-Auth-Provider": "clerk",
            "X-TradeNOC-Auth-User-Id": user_id,
            "X-TradeNOC-Auth-Email": email,
            "X-TradeNOC-Auth-Display-Name": "Live",
            "X-TradeNOC-Auth-Timestamp": timestamp,
            "X-TradeNOC-Auth-Signature": signature,
        }

    def start(self, user_id: str = "live-user", **body):
        return self.client.post("/api/v1/desk/live", headers=self.headers(user_id), json={"symbols": SYMBOLS, **body})

    def test_start_tick_stop_and_save(self) -> None:
        self.assertIsNone(self.client.get("/api/v1/desk/live", headers=self.headers()).json())
        started = self.start(notify_url="https://ntfy.sh/live-test")
        self.assertEqual(started.status_code, 200, started.text)
        body = started.json()
        self.assertEqual(body["status"], "running")
        self.assertEqual(body["notify_channel"], "ntfy")
        self.assertNotIn("notify_url", body)
        self.assertEqual(len(body["result"]["frames"]), 17)
        self.assertEqual(self.start().status_code, 409)

        self.now = at(11, 1)
        ticked = self.client.get("/api/v1/desk/live", headers=self.headers()).json()
        self.assertEqual(len(ticked["result"]["frames"]), 18)

        stopping = self.client.post(f"/api/v1/desk/live/{body['id']}/stop", headers=self.headers()).json()
        self.assertIn(stopping["status"], ("stopping", "stopped"))
        self.now = at(11, 11)
        final = self.client.get("/api/v1/desk/live", headers=self.headers()).json()
        self.assertEqual(final["status"], "stopped")
        self.assertEqual([post.headers["Title"].split(":")[0] for post in self.fake.posts], ["Paper session stopped"])
        self.assertIsNotNone(final["run_id"])
        runs = self.client.get("/api/v1/desk/runs", headers=self.headers()).json()
        self.assertEqual(runs[0]["id"], final["run_id"])
        self.assertEqual(self.client.post(f"/api/v1/desk/live/{body['id']}/stop", headers=self.headers()).status_code, 409)

    def test_rejects_bad_notify_urls_weekends_and_other_users(self) -> None:
        self.assertEqual(self.start(notify_url="https://example.com/hook").status_code, 422)
        self.now = at(11, 0, day=date(2025, 11, 29))
        self.assertEqual(self.start().status_code, 422)
        self.now = at(11, 0)
        body = self.start().json()
        other = self.headers("someone-else")
        self.assertIsNone(self.client.get("/api/v1/desk/live", headers=other).json())
        self.assertEqual(self.client.post(f"/api/v1/desk/live/{body['id']}/stop", headers=other).status_code, 404)

    def test_decision_requires_an_open_checkpoint(self) -> None:
        body = self.start(milestones=[50]).json()
        response = self.client.post(
            f"/api/v1/desk/live/{body['id']}/decision", headers=self.headers(), json={"checkpoint": 0, "decision": "continue"}
        )
        self.assertEqual(response.status_code, 409)

    def test_worker_ticks_every_active_session(self) -> None:
        self.start("worker-a")
        self.start("worker-b")
        self.now = at(12, 0)
        self.assertEqual(desk_live_service.tick_all(now=self.now), 2)
        for user_id in ("worker-a", "worker-b"):
            current = desk_live_service.latest(
                auth_module.CurrentUser("clerk", user_id, f"clerk:{user_id}", f"{user_id}@example.com")
            )
            assert current is not None and current.result is not None
            self.assertEqual(len(current.result.frames), 29)


if __name__ == "__main__":
    unittest.main()
