import sys
import tempfile
import time
import unittest
from datetime import date
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
from app.services import state_store
from app.services.desk import alpaca, historical
from app.services.desk.calendar import is_early_close, session_bar_count
from app.services.desk.engine import run_desk_session
from app.services.desk.historical import align_session, load_historical_feed
from app.services.desk.market import MarketDataError
from app.services.desk.polygon import fetch_session_bars
from app.services.desk.slots import SlotBar
from market_fakes import END_DATE, FakeAlpaca, FakePolygon

class MarketDataTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.patches = [
            patch.object(settings, "polygon_api_key", "test-polygon-key"),
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


class CalendarTests(unittest.TestCase):
    def test_early_closes(self) -> None:
        self.assertTrue(is_early_close(date(2025, 11, 28)))
        self.assertTrue(is_early_close(date(2025, 12, 24)))
        self.assertTrue(is_early_close(date(2025, 7, 3)))
        self.assertFalse(is_early_close(date(2026, 7, 3)))  # Friday: the observed holiday, not a half day
        self.assertFalse(is_early_close(date(2025, 12, 26)))
        self.assertEqual(session_bar_count(date(2025, 11, 28)), 42)
        self.assertEqual(session_bar_count(date(2025, 11, 26)), 78)


class PolygonClientTests(MarketDataTestCase):
    def test_bars_are_trimmed_to_regular_hours(self) -> None:
        fake = FakePolygon()
        with fake.client() as client:
            bars = fetch_session_bars("AAPL", date(2025, 11, 24), END_DATE, client=client)

        by_day: dict[date, list[SlotBar]] = {}
        for bar in bars:
            by_day.setdefault(bar.day, []).append(bar)
        self.assertEqual(sorted(by_day), [date(2025, 11, 24), date(2025, 11, 25), date(2025, 11, 26), END_DATE])
        self.assertEqual(len(by_day[date(2025, 11, 26)]), 78)
        self.assertEqual(len(by_day[END_DATE]), 42)
        self.assertEqual(by_day[date(2025, 11, 26)][0].slot, 0)

        request = fake.requests[0]
        self.assertEqual(request.headers["Authorization"], "Bearer test-polygon-key")
        self.assertNotIn("test-polygon-key", str(request.url))
        self.assertIn("/v2/aggs/ticker/AAPL/range/5/minute/2025-11-24/2025-11-28", str(request.url))
        self.assertEqual(request.url.params["adjusted"], "true")

    def test_follows_next_url_pages(self) -> None:
        fake = FakePolygon(page_size=500)
        with fake.client() as client:
            bars = fetch_session_bars("AAPL", date(2025, 11, 24), END_DATE, client=client)
        self.assertGreater(len(fake.requests), 1)
        self.assertTrue(all(request.headers["Authorization"] == "Bearer test-polygon-key" for request in fake.requests))
        self.assertEqual(len(bars), 78 * 3 + 42)

    def test_errors_map_to_clear_statuses(self) -> None:
        cases = [
            (429, {"status": "ERROR", "error": "too many requests"}, 429, "rate limit"),
            (403, {"status": "NOT_AUTHORIZED", "message": "plan does not include this"}, 502, "POLYGON_API_KEY"),
            (500, {"error": "boom"}, 502, "HTTP 500"),
            (200, {"status": "ERROR", "error": "bad ticker"}, 502, "bad ticker"),
        ]
        for status, body, expected_status, expected_text in cases:
            fake = FakePolygon()
            fake.status_override = (status, body)
            with self.subTest(status=status), fake.client() as client:
                with self.assertRaises(MarketDataError) as caught:
                    fetch_session_bars("AAPL", date(2025, 11, 24), END_DATE, client=client)
                self.assertEqual(caught.exception.status_code, expected_status)
                self.assertIn(expected_text, caught.exception.message)


class AlpacaClientTests(MarketDataTestCase):
    def test_one_request_covers_many_symbols_in_regular_hours(self) -> None:
        fake = FakeAlpaca()
        with fake.client() as client:
            bars = alpaca.fetch_bars(["NVDA", "AAPL"], date(2025, 11, 24), END_DATE, client=client)

        self.assertEqual(len(fake.requests), 1)
        request = fake.requests[0]
        self.assertEqual(request.url.path, "/v2/stocks/bars")
        self.assertEqual(request.headers["APCA-API-KEY-ID"], "test-alpaca-id")
        self.assertEqual(request.headers["APCA-API-SECRET-KEY"], "test-alpaca-secret")
        params = request.url.params
        self.assertEqual(params["symbols"], "NVDA,AAPL")
        self.assertEqual(params["timeframe"], "5Min")
        self.assertEqual(params["feed"], "sip")
        self.assertEqual(params["adjustment"], "split")
        self.assertEqual(params["start"], "2025-11-24T05:00:00Z")
        self.assertEqual(params["end"], "2025-11-29T01:00:00Z")

        for symbol in ("AAPL", "NVDA"):
            per_day: dict[date, int] = {}
            for bar in bars[symbol]:
                per_day[bar.day] = per_day.get(bar.day, 0) + 1
            self.assertEqual(per_day, {date(2025, 11, 24): 78, date(2025, 11, 25): 78, date(2025, 11, 26): 78, END_DATE: 42})

    def test_follows_page_tokens(self) -> None:
        fake = FakeAlpaca(page_size=300)
        with fake.client() as client:
            bars = alpaca.fetch_bars(["AAPL", "NVDA"], date(2025, 11, 24), END_DATE, client=client)
        self.assertGreater(len(fake.requests), 2)
        self.assertEqual([len(bars["AAPL"]), len(bars["NVDA"])], [78 * 3 + 42, 78 * 3 + 42])

    def test_errors_map_to_clear_statuses(self) -> None:
        cases = [
            (429, {"message": "too many requests"}, 429, "rate limit"),
            (403, {"message": "forbidden."}, 502, "ALPACA_API_KEY_ID"),
            (422, {"message": "invalid start"}, 502, "invalid start"),
        ]
        for status, body, expected_status, expected_text in cases:
            fake = FakeAlpaca()
            fake.status_override = (status, body)
            with self.subTest(status=status), fake.client() as client:
                with self.assertRaises(MarketDataError) as caught:
                    alpaca.fetch_bars(["AAPL"], date(2025, 11, 24), END_DATE, client=client)
                self.assertEqual(caught.exception.status_code, expected_status)
                self.assertIn(expected_text, caught.exception.message)

    def test_historical_run_batches_and_caches(self) -> None:
        fake = FakeAlpaca(coverage={"ILLQ": 0.2})
        config = DeskConfig(data_source="alpaca", end_date=END_DATE, sessions=2, symbols=["AAPL", "NVDA", "ILLQ"], seed=2)
        with fake.client() as client:
            first = run_desk_session(config, watchlist_symbols=[], journal_trades=[], market_client=client)
            second = run_desk_session(config, watchlist_symbols=[], journal_trades=[], market_client=client)

        # One bars request for every symbol, then one trade-print request per replayed day; the rerun is all cache.
        self.assertEqual([request.url.path for request in fake.requests], ["/v2/stocks/bars"] + ["/v2/stocks/trades"] * 2)
        self.assertEqual(first.flow_source, "trade prints")
        self.assertEqual(first.data_source, "alpaca")
        self.assertEqual(first.session_labels, ["2025-11-26", "2025-11-28"])
        self.assertEqual(first.config.symbols, ["AAPL", "NVDA"])
        plan = next(event for event in first.events if event.kind == "session_plan")
        self.assertIn("Alpaca 5-minute bars", plan.message)
        self.assertEqual(first.model_dump_json(), second.model_dump_json())

    def test_requires_both_keys(self) -> None:
        with patch.object(settings, "alpaca_api_secret_key", "replace-me"), self.assertRaises(MarketDataError) as caught:
            load_historical_feed("alpaca", ["AAPL"], END_DATE, 1)
        self.assertEqual(caught.exception.status_code, 503)
        self.assertIn("ALPACA_API_SECRET_KEY", caught.exception.message)


class AlignmentTests(unittest.TestCase):
    def test_gaps_become_flat_bars_and_thin_days_are_rejected(self) -> None:
        day = date(2025, 11, 26)
        traded = [SlotBar(day, slot, 10 + slot, 11 + slot, 9 + slot, 10.5 + slot, 100) for slot in range(78) if slot != 5]
        aligned = align_session(day, traded)
        assert aligned is not None
        self.assertEqual(len(aligned), 78)
        self.assertEqual(aligned[5].volume, 0)
        self.assertEqual(aligned[5].open, aligned[4].close)
        self.assertEqual(aligned[5].high, aligned[4].close)

        self.assertIsNone(align_session(day, traded[:30]))


class HistoricalFeedTests(MarketDataTestCase):
    def test_replays_real_sessions_with_warmup_holidays_and_half_days(self) -> None:
        fake = FakePolygon(coverage={"ILLQ": 0.2})
        config = DeskConfig(data_source="polygon", end_date=END_DATE, sessions=3, symbols=["AAPL", "NVDA", "ILLQ"], seed=4)
        with fake.client() as client:
            result = run_desk_session(config, watchlist_symbols=[], journal_trades=[], market_client=client)

        self.assertEqual(result.data_source, "polygon")
        self.assertEqual(result.session_labels, ["2025-11-25", "2025-11-26", "2025-11-28"])
        self.assertEqual(result.config.symbols, ["AAPL", "NVDA"])
        self.assertTrue(any("Dropped ILLQ: too few traded bars" in event.message for event in result.events))
        self.assertEqual(len(result.frames), 78 + 78 + 42)
        self.assertEqual([frame.clock for frame in result.frames if frame.session == 3][-1], "13:00")
        self.assertIn("historical", result.disclaimer)

        last_steps = {frame.session: frame.step for frame in result.frames}
        for trade in result.trades:
            self.assertEqual(trade.session, next(f.session for f in result.frames if f.step == trade.close_step))
            self.assertLessEqual(trade.close_step, last_steps[trade.session])
        for frame in result.frames:
            if frame.step == last_steps[frame.session]:
                self.assertEqual(frame.positions, [])

    def test_fills_use_the_next_real_bar_open(self) -> None:
        fake = FakePolygon()
        config = DeskConfig(data_source="polygon", end_date=END_DATE, sessions=3, symbols=["AAPL", "NVDA", "SPY", "QQQ"], seed=4)
        with fake.client() as client:
            result = run_desk_session(config, watchlist_symbols=[], journal_trades=[], market_client=client)
            feed, _ = load_historical_feed("polygon", config.symbols, END_DATE, 3, client=client)

        first_step = {}
        for frame in result.frames:
            first_step.setdefault(frame.session, frame.step)
        slippage = config.slippage_bps / 10_000
        self.assertGreater(len(result.trades), 0)
        for trade in result.trades:
            bar = feed.session_bars(trade.symbol, trade.session)[trade.open_step - first_step[trade.session]]
            direction = 1 if trade.side == "long" else -1
            self.assertAlmostEqual(trade.entry, bar.open * (1 + direction * slippage), places=3)

    def test_cache_makes_replays_free(self) -> None:
        fake = FakePolygon()
        config = DeskConfig(data_source="polygon", end_date=END_DATE, sessions=2, symbols=["AAPL", "NVDA"], seed=1)
        with fake.client() as client:
            first = run_desk_session(config, watchlist_symbols=[], journal_trades=[], market_client=client)
            requests_after_first = len(fake.requests)
            second = run_desk_session(config, watchlist_symbols=[], journal_trades=[], market_client=client)

        self.assertEqual(requests_after_first, 2)
        self.assertEqual(len(fake.requests), 2)
        self.assertEqual(first.model_dump_json(), second.model_dump_json())

    def test_unknown_tickers_are_dropped_with_a_reason(self) -> None:
        fake = FakePolygon(coverage={"ZZZZ": 0.0})
        with fake.client() as client:
            feed, notes = load_historical_feed("polygon", ["AAPL", "ZZZZ"], END_DATE, 1, client=client)
        self.assertEqual(feed.symbols, ["AAPL"])
        self.assertIn("check the ticker", notes[0])

    def test_rate_limit_keeps_what_was_loaded(self) -> None:
        fake = FakePolygon()
        with fake.client() as client:
            load_historical_feed("polygon", ["AAPL"], END_DATE, 2, client=client)
            fake.status_override = (429, {"status": "ERROR"})
            with self.assertRaises(MarketDataError) as caught:
                load_historical_feed("polygon", ["AAPL", "NVDA"], END_DATE, 2, client=client)
        self.assertEqual(caught.exception.status_code, 429)
        self.assertEqual([request.url.path.split("/")[4] for request in fake.requests], ["AAPL", "NVDA"])

    def test_rejects_unconfigured_and_unfinished_days(self) -> None:
        with patch.object(settings, "polygon_api_key", "replace-me"), self.assertRaises(MarketDataError) as caught:
            load_historical_feed("polygon", ["AAPL"], END_DATE, 1)
        self.assertEqual(caught.exception.status_code, 503)

        with patch.object(historical, "market_today", return_value=END_DATE), self.assertRaises(MarketDataError) as caught:
            load_historical_feed("polygon", ["AAPL"], END_DATE, 1)
        self.assertEqual(caught.exception.status_code, 422)

    def test_not_enough_trading_days(self) -> None:
        fake = FakePolygon()
        with fake.client() as client, patch.object(historical, "history_window", return_value=date(2025, 11, 26)):
            with self.assertRaises(MarketDataError) as caught:
                load_historical_feed("polygon", ["AAPL"], END_DATE, 3, client=client)
        self.assertEqual(caught.exception.status_code, 422)
        self.assertIn("needs 4", caught.exception.message)


class MarketDataApiTests(MarketDataTestCase):
    def setUp(self) -> None:
        super().setUp()
        temp_path = Path(self.temp_dir.name)
        seed_copy = temp_path / "seed_state.json"
        seed_copy.write_text(state_store.SEED_PATH.read_text(encoding="utf-8"), encoding="utf-8")
        self.fake = FakePolygon()
        api_patches = [
            patch.object(settings, "auth_mode", "clerk"),
            patch.object(settings, "persistence_mode", "file"),
            patch.object(settings, "auth_internal_shared_secret", "test-shared-secret"),
            patch.object(settings, "app_env", "test"),
            patch.object(state_store, "DATA_DIR", temp_path),
            patch.object(state_store, "SEED_PATH", seed_copy),
            patch.object(state_store, "STORE_PATH", temp_path / "store_state.json"),
            patch.object(historical, "_http_client", self.fake.client),
        ]
        for active_patch in api_patches:
            active_patch.start()
        self.patches.extend(api_patches)
        state_store.reset_state_from_seed()
        self.client = TestClient(create_application())

    def tearDown(self) -> None:
        self.client.close()
        super().tearDown()

    def headers(self) -> dict[str, str]:
        timestamp = str(int(time.time()))
        signature = auth_module._build_signature(
            auth_provider="clerk",
            auth_user_id="market-user",
            auth_email="market@example.com",
            auth_display_name="Market",
            auth_timestamp=timestamp,
        )
        return {
            "X-TradeNOC-Auth-Provider": "clerk",
            "X-TradeNOC-Auth-User-Id": "market-user",
            "X-TradeNOC-Auth-Email": "market@example.com",
            "X-TradeNOC-Auth-Display-Name": "Market",
            "X-TradeNOC-Auth-Timestamp": timestamp,
            "X-TradeNOC-Auth-Signature": signature,
        }

    def test_sources_report_availability(self) -> None:
        sources = {item["id"]: item for item in self.client.get("/api/v1/desk/sources", headers=self.headers()).json()}
        self.assertEqual(list(sources), ["synthetic", "polygon", "alpaca"])
        self.assertTrue(sources["polygon"]["available"])
        self.assertTrue(sources["alpaca"]["available"])
        with patch.object(settings, "polygon_api_key", "replace-me"):
            sources = {item["id"]: item for item in self.client.get("/api/v1/desk/sources", headers=self.headers()).json()}
        self.assertFalse(sources["polygon"]["available"])
        self.assertIn("POLYGON_API_KEY", sources["polygon"]["detail"])

    def test_historical_run_is_saved_and_reloadable(self) -> None:
        body = {"data_source": "polygon", "end_date": END_DATE.isoformat(), "sessions": 1, "symbols": ["AAPL", "NVDA"]}
        created = self.client.post("/api/v1/desk/runs", headers=self.headers(), json=body)
        self.assertEqual(created.status_code, 200, created.text)
        run = created.json()
        self.assertEqual(run["data_source"], "polygon")
        self.assertEqual(run["config"]["end_date"], "2025-11-28")
        self.assertEqual(run["session_labels"], ["2025-11-28"])

        fetched = self.client.get(f"/api/v1/desk/runs/{run['id']}", headers=self.headers())
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.json()["session_labels"], ["2025-11-28"])
        listed = self.client.get("/api/v1/desk/runs", headers=self.headers()).json()
        self.assertEqual(listed[0]["data_source"], "polygon")

    def test_market_data_errors_surface_with_detail(self) -> None:
        self.fake.status_override = (403, {"status": "NOT_AUTHORIZED", "message": "plan does not include this"})
        response = self.client.post(
            "/api/v1/desk/runs",
            headers=self.headers(),
            json={"data_source": "polygon", "end_date": END_DATE.isoformat(), "symbols": ["AAPL"]},
        )
        self.assertEqual(response.status_code, 502)
        self.assertIn("plan does not include this", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
