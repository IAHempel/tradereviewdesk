"""Historical market feed: real Polygon or Alpaca bars for recent sessions, cached on disk.

Historical bars do not change once a day is over, so each (symbol, window)
request is cached as soon as it is fetched. That matters on Polygon's free plan
(5 requests a minute): a rate-limited run keeps what it already loaded, and
replaying the same days costs no requests at all.
"""

import json
import os
import tempfile
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta

import httpx

from app.core.config import settings
from app.services.desk import alpaca, polygon
from app.services.desk.calendar import market_today, session_bar_count
from app.services.desk.market import Bar, MarketDataError
from app.services.desk.slots import SlotBar

MIN_SLOT_COVERAGE = 0.5
CACHE_VERSION = 1


@dataclass(frozen=True)
class HistoricalProvider:
    id: str
    name: str
    is_configured: Callable[[], bool]
    missing_config: str
    fetch: Callable[..., dict[str, list[SlotBar]]]
    batch_size: int


PROVIDERS: dict[str, HistoricalProvider] = {
    "polygon": HistoricalProvider(
        id="polygon",
        name="Polygon",
        is_configured=lambda: settings.is_polygon_configured,
        missing_config="Polygon isn't configured on the API. Set POLYGON_API_KEY to replay historical bars.",
        fetch=polygon.fetch_bars,
        batch_size=1,
    ),
    "alpaca": HistoricalProvider(
        id="alpaca",
        name="Alpaca",
        is_configured=lambda: settings.is_alpaca_configured,
        missing_config=(
            "Alpaca isn't configured on the API. Set ALPACA_API_KEY_ID and ALPACA_API_SECRET_KEY to replay historical bars."
        ),
        fetch=alpaca.fetch_bars,
        batch_size=50,
    ),
}


def _http_client() -> httpx.Client:
    return httpx.Client()


def history_window(end_date: date, sessions: int) -> date:
    """Calendar start date that holds `sessions` + 1 trading days (one warmup) through `end_date`."""
    return end_date - timedelta(days=(sessions + 1) * 2 + 7)


def _cache_file(provider: str, symbol: str, start: date, end: date):
    return settings.market_data_cache_path / provider / f"{symbol}_{start.isoformat()}_{end.isoformat()}_5m_adj.json"


def _read_cache(provider: str, symbol: str, start: date, end: date) -> list[SlotBar] | None:
    path = _cache_file(provider, symbol, start, end)
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


def _write_cache(provider: str, symbol: str, start: date, end: date, bars: list[SlotBar]) -> None:
    path = _cache_file(provider, symbol, start, end)
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


def group_by_day(slot_bars: list[SlotBar]) -> dict[date, list[SlotBar]]:
    grouped: dict[date, list[SlotBar]] = defaultdict(list)
    for bar in slot_bars:
        grouped[bar.day].append(bar)
    return grouped


class HistoricalMarketFeed:
    def __init__(self, data_source: str, days: list[date], tape: dict[str, dict[date, list[Bar]]]) -> None:
        self.data_source = data_source
        self.days = days
        self.symbols = list(tape)
        self.session_labels = [day.isoformat() for day in days[1:]]
        self._tape = tape

    def session_bars(self, symbol: str, session: int) -> list[Bar]:
        return self._tape[symbol][self.days[session]]


def build_feed(
    provider: HistoricalProvider,
    by_symbol: dict[str, dict[date, list[SlotBar]]],
    days: list[date],
) -> tuple[HistoricalMarketFeed, list[str]]:
    """Aligns each symbol's bars on `days`, dropping symbols too thin to replay. Returns the feed plus notes."""
    tape: dict[str, dict[date, list[Bar]]] = {}
    notes: list[str] = []
    for symbol, grouped in by_symbol.items():
        if not grouped:
            notes.append(f"Dropped {symbol}: {provider.name} returned no bars for it in this window (check the ticker).")
            continue
        aligned = {day: align_session(day, grouped.get(day, [])) for day in days}
        thin_days = [day.isoformat() for day, bars in aligned.items() if bars is None]
        if thin_days:
            notes.append(f"Dropped {symbol}: too few traded bars on {', '.join(thin_days)}.")
            continue
        tape[symbol] = {day: bars for day, bars in aligned.items() if bars is not None}

    if not tape:
        raise MarketDataError("None of the symbols had enough regular-session bars to replay those days.", status_code=422)

    return HistoricalMarketFeed(provider.id, days, tape), notes


def fetch_cached(
    provider: HistoricalProvider,
    symbols: list[str],
    start: date,
    end: date,
    *,
    client: httpx.Client,
) -> dict[str, list[SlotBar]]:
    """Bars per symbol for a completed window, from the cache where possible.

    Uncached symbols are fetched in provider-sized batches and cached as each batch lands,
    so a rate limit part-way through keeps the symbols already loaded.
    """
    loaded: dict[str, list[SlotBar]] = {}
    missing: list[str] = []
    for symbol in symbols:
        cached = _read_cache(provider.id, symbol, start, end)
        if cached is None:
            missing.append(symbol)
        else:
            loaded[symbol] = cached

    for index in range(0, len(missing), provider.batch_size):
        batch = missing[index : index + provider.batch_size]
        for symbol, slot_bars in provider.fetch(batch, start, end, client=client).items():
            if slot_bars:
                _write_cache(provider.id, symbol, start, end, slot_bars)
            loaded[symbol] = slot_bars

    return {symbol: loaded.get(symbol, []) for symbol in symbols}


def load_historical_feed(
    source: str,
    symbols: list[str],
    end_date: date,
    sessions: int,
    *,
    client: httpx.Client | None = None,
) -> tuple[HistoricalMarketFeed, list[str]]:
    """Returns the feed plus notes about symbols that had to be dropped."""
    provider = PROVIDERS[source]
    if not provider.is_configured():
        raise MarketDataError(provider.missing_config, status_code=503)
    if end_date >= market_today():
        raise MarketDataError("Pick a replay date before today; the desk only replays completed sessions.", status_code=422)

    start = history_window(end_date, sessions)
    owns_client = client is None
    http = client or _http_client()
    try:
        fetched = fetch_cached(provider, symbols, start, end_date, client=http)
    finally:
        if owns_client:
            http.close()

    by_symbol = {symbol: group_by_day(slot_bars) for symbol, slot_bars in fetched.items()}
    trading_days = sorted({day for grouped in by_symbol.values() for day in grouped})
    needed = sessions + 1
    if len(trading_days) < needed:
        raise MarketDataError(
            f"{provider.name} returned {len(trading_days)} trading day(s) of 5-minute bars between {start} and {end_date}; "
            f"this run needs {needed} (one warmup session plus {sessions}). Try a later date or fewer sessions.",
            status_code=422,
        )

    return build_feed(provider, by_symbol, trading_days[-needed:])
