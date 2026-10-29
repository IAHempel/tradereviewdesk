import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.core import auth as auth_module
from app.core.config import settings
from app.main import create_application
from app.schemas.desk import DeskConfig
from app.schemas.trades import TradeEntryResponse
from app.services import state_store
from app.services.desk.engine import journal_counts, run_desk_session
from app.services.desk.market import BARS_PER_SESSION, SimulatedMarketFeed
from app.services.desk.stats import run_monte_carlo

SYMBOLS = ["AAPL", "NVDA", "SPY", "QQQ"]


def run(**overrides):
    config = DeskConfig(**{"symbols": SYMBOLS, "seed": 11, "sessions": 3, **overrides})
    return run_desk_session(config, watchlist_symbols=[], journal_trades=[])


class DeskEngineTests(unittest.TestCase):
    def test_same_seed_replays_identically(self) -> None:
        self.assertEqual(run().model_dump_json(), run().model_dump_json())
        self.assertNotEqual(run().model_dump_json(), run(seed=12).model_dump_json())

    def test_fills_happen_at_the_next_bar_open(self) -> None:
        config = DeskConfig(symbols=SYMBOLS, seed=11, sessions=3)
        result = run_desk_session(config, watchlist_symbols=[], journal_trades=[])
        feed = SimulatedMarketFeed(SYMBOLS, 11, 3)
        slippage = config.slippage_bps / 10_000
        order_steps = {
            event.message.split("(")[-1].rstrip(")."): event.step for event in result.events if event.kind == "order"
        }

        self.assertGreater(len(result.trades), 0)
        for trade in result.trades:
            bar = feed.session_bars(trade.symbol, trade.session)[trade.open_step % BARS_PER_SESSION]
            direction = 1 if trade.side == "long" else -1
            self.assertAlmostEqual(trade.entry, bar.open * (1 + direction * slippage), places=3)
            self.assertEqual(order_steps[trade.id], trade.open_step - 1)

    def test_stops_only_tighten(self) -> None:
        result = run(sessions=5, trail_after_r=0.5)
        self.assertGreater(result.pipeline.stops_trailed, 0)
        self.assertEqual(result.pipeline.stops_widened, 0)
        for trade in result.trades:
            direction = 1 if trade.side == "long" else -1
            self.assertGreaterEqual(direction * (trade.stop_final - trade.stop_initial), 0)

    def test_position_limits_and_flat_by_the_bell(self) -> None:
        result = run(sessions=5, max_open_positions=2)
        for frame in result.frames:
            self.assertLessEqual(len(frame.positions), 2)
            if frame.step % BARS_PER_SESSION == BARS_PER_SESSION - 1:
                self.assertEqual(frame.positions, [])
        for trade in result.trades:
            self.assertEqual(trade.open_step // BARS_PER_SESSION, trade.close_step // BARS_PER_SESSION)

    def test_risk_never_exceeds_the_cap(self) -> None:
        result = run(sessions=5, risk_per_trade_pct=0.5, max_leverage=4)
        peak_equity = max(frame.equity for frame in result.frames)
        for trade in result.trades:
            # Planned risk is capped at 0.5% of equity; allow for slippage between signal and fill.
            self.assertLessEqual(trade.risk_dollars, peak_equity * 0.005 * 1.25)

    def test_daily_loss_halt_stops_new_orders(self) -> None:
        result = run(sessions=5, max_daily_loss_pct=0.2)
        halts = [event for event in result.events if event.kind == "halt"]
        self.assertGreater(len(halts), 0)
        for halt in halts:
            later_orders = [
                event
                for event in result.events
                if event.kind == "order" and event.session == halt.session and event.step >= halt.step
            ]
            self.assertEqual(later_orders, [])
        self.assertEqual(result.summary.halted_sessions, len(halts))

    def test_only_enabled_setups_trade(self) -> None:
        result = run(sessions=5, allowed_setups=["breakout"])
        self.assertTrue(all(trade.setup == "breakout" for trade in result.trades))

    def test_tape_lines_up_with_frames(self) -> None:
        result = run()
        feed = SimulatedMarketFeed(SYMBOLS, 11, 3)
        for symbol in SYMBOLS:
            self.assertEqual(len(result.tape[symbol]), len(result.frames))
            bar = feed.session_bars(symbol, 2)[5]
            self.assertEqual(result.tape[symbol][BARS_PER_SESSION + 5], [bar.open, bar.high, bar.low, bar.close, bar.volume])

    def test_milestones_are_validated(self) -> None:
        self.assertEqual(DeskConfig(milestones=[1.05, 1.01, 1.05]).milestones, [1.01, 1.05])
        with self.assertRaises(ValueError):
            DeskConfig(milestones=[0.9])

    def test_equity_accounting_balances(self) -> None:
        result = run(sessions=4)
        summary = result.summary
        self.assertAlmostEqual(summary.ending_balance, summary.starting_balance + sum(t.pnl for t in result.trades), delta=0.05)
        self.assertAlmostEqual(result.frames[-1].equity, summary.ending_balance, delta=0.01)
        self.assertEqual(summary.trades, summary.wins + summary.losses)
        self.assertEqual(result.pipeline.logger_reasons, len(result.events))

    def test_journal_tags_feed_setup_priors(self) -> None:
        def trade(tags: list[str], pnl: float) -> TradeEntryResponse:
            return TradeEntryResponse(
                id="t", trade_date="2026-10-01", symbol="AAPL", asset_type="stock", side="long", pnl=pnl, tags=tags
            )

        counts = journal_counts(
            [
                trade(["opening-range"], 120),
                trade(["Breakout", "a+"], -40),
                trade(["vwap-reclaim"], 15),
                trade(["untagged-idea"], 30),
                trade(["fade"], 0),
            ]
        )
        self.assertEqual(counts, {"breakout": (1, 1), "sweep_reclaim": (1, 0)})

    def test_monte_carlo_needs_a_sample_and_orders_its_bands(self) -> None:
        self.assertIsNone(run_monte_carlo([0.01, -0.01], seed=1))
        fan = run_monte_carlo([0.012, -0.006, -0.005, 0.01, -0.004, 0.002], seed=1)
        assert fan is not None
        for band in fan.bands:
            self.assertLessEqual(band.p5, band.p25)
            self.assertLessEqual(band.p25, band.p50)
            self.assertLessEqual(band.p50, band.p75)
            self.assertLessEqual(band.p75, band.p95)
        self.assertEqual(fan.bands[0].trade_index, 0)
        self.assertEqual(fan.bands[-1].trade_index, fan.trades_per_path)

    def test_short_watchlists_are_topped_up(self) -> None:
        result = run_desk_session(DeskConfig(seed=3), watchlist_symbols=["aapl"], journal_trades=[])
        self.assertEqual(result.config.symbols[0], "AAPL")
        self.assertGreaterEqual(len(result.config.symbols), 4)
        self.assertTrue(any(event.kind == "symbols" for event in result.events))


class DeskApiTests(unittest.TestCase):
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

    def auth_headers(self, user_id: str = "desk-user") -> dict[str, str]:
        timestamp = str(int(time.time()))
        email = f"{user_id}@example.com"
        signature = auth_module._build_signature(
            auth_provider="clerk",
            auth_user_id=user_id,
            auth_email=email,
            auth_display_name="Desk User",
            auth_timestamp=timestamp,
        )
        return {
            "X-TradeNOC-Auth-Provider": "clerk",
            "X-TradeNOC-Auth-User-Id": user_id,
            "X-TradeNOC-Auth-Email": email,
            "X-TradeNOC-Auth-Display-Name": "Desk User",
            "X-TradeNOC-Auth-Timestamp": timestamp,
            "X-TradeNOC-Auth-Signature": signature,
        }

    def test_defaults_use_the_watchlist(self) -> None:
        response = self.client.get("/api/v1/desk/defaults", headers=self.auth_headers())
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["symbols"][:2], ["AAPL", "NVDA"])
        self.assertIsNone(body["seed"])

    def test_runs_are_saved_and_scoped_per_user(self) -> None:
        headers = self.auth_headers()
        created = self.client.post("/api/v1/desk/runs", headers=headers, json={"seed": 5, "sessions": 2})
        self.assertEqual(created.status_code, 200)
        run = created.json()
        self.assertEqual(run["mode"], "paper")
        self.assertEqual(run["data_source"], "synthetic")
        self.assertEqual(run["config"]["seed"], 5)
        self.assertEqual(run["session_labels"], ["Session 1", "Session 2"])
        self.assertEqual(len(run["frames"]), 2 * BARS_PER_SESSION)

        listed = self.client.get("/api/v1/desk/runs", headers=headers).json()
        self.assertEqual([item["id"] for item in listed], [run["id"]])
        self.assertNotIn("frames", listed[0])

        fetched = self.client.get(f"/api/v1/desk/runs/{run['id']}", headers=headers)
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.json()["summary"], run["summary"])

        other = self.auth_headers("someone-else")
        self.assertEqual(self.client.get(f"/api/v1/desk/runs/{run['id']}", headers=other).status_code, 404)
        self.assertEqual(self.client.get("/api/v1/desk/runs", headers=other).json(), [])

    def test_rejects_out_of_bounds_risk(self) -> None:
        response = self.client.post("/api/v1/desk/runs", headers=self.auth_headers(), json={"risk_per_trade_pct": 10})
        self.assertEqual(response.status_code, 422)

    def test_requires_auth(self) -> None:
        self.assertEqual(self.client.post("/api/v1/desk/runs", json={}).status_code, 401)


if __name__ == "__main__":
    unittest.main()
