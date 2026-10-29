import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.core.config import settings
from app.schemas.desk import DeskConfig
from app.services.desk import alpaca
from app.services.desk.agents import DeskGate, FilterAgent, Setup
from app.services.desk.engine import run_desk_session
from app.services.desk.flow import FLOW_MIN_BARS, FlowMemory, FlowSlot, TickRuleClassifier, proxy_flow
from app.services.desk.market import Bar
from market_fakes import END_DATE, FakeAlpaca


def setup(kind: str, side: str) -> Setup:
    return Setup("AAPL", kind, side, 100.0, 99.0 if side == "long" else 101.0, 103.0 if side == "long" else 97.0, 1.0, 1.5, True, "test")


def gate(flow: float) -> DeskGate:
    return DeskGate(
        bar_index=20, session_length=78, halted=False, cooldown_until=-1, step=20, busy_symbols=set(), working_count=0, flow=flow
    )


class FlowMathTests(unittest.TestCase):
    def test_tick_rule(self) -> None:
        classifier = TickRuleClassifier()
        self.assertEqual([classifier.side(price) for price in (10.0, 10.1, 10.1, 10.0, 10.0)], [0, 1, 1, -1, -1])

    def test_bar_proxy_splits_volume_by_close_location(self) -> None:
        self.assertEqual(proxy_flow(Bar(0, 10, 11, 9, 11, 100)), FlowSlot(100, 0))
        self.assertEqual(proxy_flow(Bar(0, 10, 11, 9, 9, 100)), FlowSlot(0, 100))
        self.assertEqual(proxy_flow(Bar(0, 10, 11, 9, 10, 100)), FlowSlot(50, 50))
        self.assertEqual(proxy_flow(Bar(0, 10, 10, 10, 10, 100)), FlowSlot(50, 50))

    def test_memory_shrinks_early_readings_and_forgets_old_bars(self) -> None:
        memory = FlowMemory()
        first = memory.push(FlowSlot(100, 0))
        self.assertAlmostEqual(first, 1 / FLOW_MIN_BARS)
        self.assertFalse(memory.warmed_up)
        for _ in range(FLOW_MIN_BARS):
            reading = memory.push(FlowSlot(100, 0))
        self.assertTrue(memory.warmed_up)
        self.assertAlmostEqual(reading, 1.0)
        for _ in range(30):
            reading = memory.push(FlowSlot(0, 100))
        self.assertAlmostEqual(reading, -1.0)
        self.assertEqual(len(memory.slots), 24)


class FlowRulesTests(unittest.TestCase):
    def test_flow_vetoes_continuation_setups_only(self) -> None:
        rules = FilterAgent(DeskConfig(flow_veto=0.35))
        self.assertEqual(rules.review(setup("breakout", "long"), gate(-0.4)), "flow_against")
        self.assertEqual(rules.review(setup("trend_pullback", "short"), gate(0.4)), "flow_against")
        self.assertIsNone(rules.review(setup("breakout", "long"), gate(-0.2)))
        self.assertIsNone(rules.review(setup("breakout", "long"), gate(0.6)))
        self.assertIsNone(rules.review(setup("mean_reversion", "long"), gate(-0.9)))
        self.assertIsNone(rules.review(setup("sweep_reclaim", "long"), gate(-0.9)))

    def test_engine_records_flow_and_counts_vetoes(self) -> None:
        result = run_desk_session(
            DeskConfig(symbols=["AAPL", "NVDA", "SPY", "QQQ"], seed=9, sessions=5, flow_veto=0.05),
            watchlist_symbols=[],
            journal_trades=[],
        )
        self.assertEqual(result.flow_source, "bar proxy")
        self.assertTrue(all(set(frame.flow) == {"AAPL", "NVDA", "SPY", "QQQ"} for frame in result.frames))
        self.assertTrue(all(-1 <= value <= 1 for frame in result.frames for value in frame.flow.values()))
        vetoes = [event for event in result.events if event.kind == "veto"]
        self.assertGreater(len(vetoes), 0)
        self.assertEqual(result.pipeline.flow_vetoes, len(vetoes))


class TradeFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.patches = [
            patch.object(settings, "alpaca_api_key_id", "test-alpaca-id"),
            patch.object(settings, "alpaca_api_secret_key", "test-alpaca-secret"),
            patch.object(settings, "market_data_cache_dir", self.temp_dir.name),
        ]
        for active_patch in self.patches:
            active_patch.start()

    def tearDown(self) -> None:
        for active_patch in reversed(self.patches):
            active_patch.stop()
        self.temp_dir.cleanup()

    def test_prints_become_tick_rule_flow_per_slot(self) -> None:
        fake = FakeAlpaca(page_size=400)
        with fake.client() as client:
            flows = alpaca.fetch_trade_flow(["AAPL", "NVDA"], date(2025, 11, 26), client=client)
            half_day = alpaca.fetch_trade_flow(["AAPL"], END_DATE, client=client)

        first = fake.requests[0].url.params
        self.assertEqual(fake.requests[0].url.path, "/v2/stocks/trades")
        self.assertEqual(first["feed"], "iex")
        self.assertEqual(first["start"], "2025-11-26T14:30:00Z")
        self.assertEqual(first["end"], "2025-11-26T21:00:00Z")
        self.assertGreater(len(fake.requests), 2)
        self.assertEqual(fake.requests[-1].url.params["end"], "2025-11-28T18:00:00Z")

        for symbol in ("AAPL", "NVDA"):
            slots = flows[symbol]
            self.assertEqual(len(slots), 78)
            self.assertTrue(all(slot.total > 0 for slot in slots))
            first_hour = sum(slot.signed for slot in slots[:12]) / sum(slot.total for slot in slots[:12])
            self.assertGreater(first_hour, 0.1)
        self.assertEqual(len(half_day["AAPL"]), 42)

    def test_failed_prints_fall_back_to_the_bar_proxy(self) -> None:
        fake = FakeAlpaca()
        fake.trades_status = (403, {"message": "forbidden."})
        config = DeskConfig(data_source="alpaca", end_date=END_DATE, sessions=1, symbols=["AAPL", "NVDA"], seed=3)
        with fake.client() as client:
            result = run_desk_session(config, watchlist_symbols=[], journal_trades=[], market_client=client)
        self.assertEqual(result.flow_source, "bar proxy")
        self.assertTrue(any("fell back to the bar proxy" in event.message for event in result.events))

    def test_trade_flow_can_be_turned_off(self) -> None:
        fake = FakeAlpaca()
        config = DeskConfig(
            data_source="alpaca", end_date=END_DATE, sessions=1, symbols=["AAPL"], seed=3, use_trade_flow=False
        )
        with fake.client() as client:
            result = run_desk_session(config, watchlist_symbols=[], journal_trades=[], market_client=client)
        self.assertEqual([request.url.path for request in fake.requests], ["/v2/stocks/bars"])
        self.assertEqual(result.flow_source, "bar proxy")


if __name__ == "__main__":
    unittest.main()
