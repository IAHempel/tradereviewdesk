"""Historical market feed: real Polygon bars for recent sessions, cached on disk.

Historical bars do not change once a day is over, so each (symbol, window)
request is cached as soon as it is fetched. That matters on Polygon's free plan
(5 requests a minute): a rate-limited run keeps what it already loaded, and
replaying the same days costs no requests at all.
"""

import json
import os
import tempfile
from collections import defaultdict
from datetime import date, timedelta

import httpx

from app.core.config import settings
from app.services.desk.calendar import market_today, session_bar_count
from app.services.desk.market import Bar, MarketDataError
from app.services.desk.polygon import SlotBar, fetch_session_bars

MIN_SLOT_COVERAGE = 0.5
CACHE_VERSION = 1


def _http_client() -> httpx.Client:
    return httpx.Client()


def history_window(end_date: date, sessions: int) -> date:
    """Calendar start date that holds `sessions` + 1 trading days (one warmup) through `end_date`."""
    return end_date - timedelta(days=(sessions + 1) * 2 + 7)


def _cache_file(symbol: str, start: date, end: date):
    return settings.market_data_cache_path / "polygon" / f"{symbol}_{start.isoformat()}_{end.isoformat()}_5m_adj.json"


def _read_cache(symbol: str, start: date, end: date) -> list[SlotBar] | None:
    path = _cache_file(symbol, start, end)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if payload.get("version") != CACHE_VERSION:
        return None
    return [
        SlotBar(date.fromisoformat(day), slot, open_, high, low, close, volume)
        for day, slot, open_, high, low, close, volume in payload["bars"]
    ]


def _write_cache(symbol: str, start: date, end: date, bars: list[SlotBar]) -> None:
    path = _cache_file(symbol, start, end)
    payload = {
        "version": CACHE_VERSION,
        "bars": [[bar.day.isoformat(), bar.slot, bar.open, bar.high, bar.low, bar.close, bar.volume] for bar in bars],
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False, encoding="utf-8") as handle:
            json.dump(payload, handle)
        os.replace(handle.name, path)
    except OSError:
        # The cache only saves requests; a read-only disk should not fail the run.
        pass


def align_session(day: date, slot_bars: list[SlotBar]) -> list[Bar] | None:
    """One bar per 5-minute slot. Slots with no trades become flat zero-volume bars at the last close.

    Returns None when fewer than half the slots traded, which is too thin to replay honestly.
    """
    slot_count = session_bar_count(day)
    by_slot = {bar.slot: bar for bar in slot_bars}
    if len(by_slot) < slot_count * MIN_SLOT_COVERAGE:
        return None

    first = by_slot[min(by_slot)]
    last_close = first.open
    bars: list[Bar] = []
    for slot in range(slot_count):
        traded = by_slot.get(slot)
        if traded is None:
            bars.append(Bar(slot, last_close, last_close, last_close, last_close, 0))
            continue
        bars.append(Bar(slot, traded.open, traded.high, traded.low, traded.close, traded.volume))
        last_close = traded.close
    return bars


class HistoricalMarketFeed:
    data_source = "polygon"

    def __init__(self, days: list[date], tape: dict[str, dict[date, list[Bar]]]) -> None:
        self.days = days
        self.symbols = list(tape)
        self.session_labels = [day.isoformat() for day in days[1:]]
        self._tape = tape

    def session_bars(self, symbol: str, session: int) -> list[Bar]:
        return self._tape[symbol][self.days[session]]


def load_polygon_feed(
    symbols: list[str],
    end_date: date,
    sessions: int,
    *,
    client: httpx.Client | None = None,
) -> tuple[HistoricalMarketFeed, list[str]]:
    """Returns the feed plus notes about symbols that had to be dropped."""
    if not settings.is_polygon_configured:
        raise MarketDataError(
            "Polygon isn't configured on the API. Set POLYGON_API_KEY to replay historical bars.", status_code=503
        )
    if end_date >= market_today():
        raise MarketDataError("Pick a replay date before today; the desk only replays completed sessions.", status_code=422)

    start = history_window(end_date, sessions)
    owns_client = client is None
    http = client or _http_client()
    by_symbol: dict[str, dict[date, list[SlotBar]]] = {}
    try:
        for symbol in symbols:
            slot_bars = _read_cache(symbol, start, end_date)
            if slot_bars is None:
                slot_bars = fetch_session_bars(symbol, start, end_date, client=http)
                if slot_bars:
                    _write_cache(symbol, start, end_date, slot_bars)
            grouped: dict[date, list[SlotBar]] = defaultdict(list)
            for bar in slot_bars:
                grouped[bar.day].append(bar)
            by_symbol[symbol] = grouped
    finally:
        if owns_client:
            http.close()

    trading_days = sorted({day for grouped in by_symbol.values() for day in grouped})
    needed = sessions + 1
    if len(trading_days) < needed:
        raise MarketDataError(
            f"Polygon returned {len(trading_days)} trading day(s) of 5-minute bars between {start} and {end_date}; "
            f"this run needs {needed} (one warmup session plus {sessions}). Try a later date or fewer sessions.",
            status_code=422,
        )

    days = trading_days[-needed:]
    tape: dict[str, dict[date, list[Bar]]] = {}
    notes: list[str] = []
    for symbol, grouped in by_symbol.items():
        if not grouped:
            notes.append(f"Dropped {symbol}: Polygon returned no bars for it in this window (check the ticker).")
            continue
        aligned = {day: align_session(day, grouped.get(day, [])) for day in days}
        thin_days = [day.isoformat() for day, bars in aligned.items() if bars is None]
        if thin_days:
            notes.append(f"Dropped {symbol}: too few traded bars on {', '.join(thin_days)}.")
            continue
        tape[symbol] = {day: bars for day, bars in aligned.items() if bars is not None}

    if not tape:
        raise MarketDataError("None of the symbols had enough regular-session bars to replay those days.", status_code=422)

    return HistoricalMarketFeed(days, tape), notes
