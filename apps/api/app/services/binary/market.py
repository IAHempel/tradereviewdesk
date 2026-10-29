"""1-minute crypto candles for the binary desk: Coinbase's public market data, or a synthetic tape.

Coinbase serves at most 300 candles per request, newest first, and omits minutes
with no trades; this module pages through the window, fills empty minutes with
flat bars at the last close, and caches completed windows on disk.
"""

import hashlib
import json
import math
import os
import random
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx

from app.core.config import settings
from app.services.desk.market import MarketDataError

CANDLES_PER_REQUEST = 300
MIN_COVERAGE = 0.8
CACHE_VERSION = 1

# Rough starting levels and daily volatility for the synthetic tape only.
SYNTHETIC_PROFILE: dict[str, tuple[float, float]] = {
    "BTC": (68_000.0, 0.028),
    "ETH": (3_400.0, 0.035),
    "SOL": (165.0, 0.05),
    "XRP": (0.62, 0.045),
    "DOGE": (0.16, 0.055),
}


@dataclass(frozen=True)
class MinuteBar:
    t: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


def _stable_seed(*parts: object) -> int:
    return int.from_bytes(hashlib.sha256("|".join(str(part) for part in parts).encode()).digest()[:8], "big")


def synthetic_minutes(asset: str, start: datetime, minutes: int, seed: int) -> list[MinuteBar]:
    """A seeded random walk with volatility regimes; no drift, so no direction is baked in."""
    price, daily_vol = SYNTHETIC_PROFILE[asset]
    rng = random.Random(_stable_seed(seed, asset))
    sigma = daily_vol / math.sqrt(1440)
    regime = 1.0
    bars: list[MinuteBar] = []
    for index in range(minutes):
        if rng.random() < 0.01:
            regime = rng.choice((0.6, 1.0, 1.6))
        step = rng.gauss(0.0, sigma * regime)
        if rng.random() < 0.002:
            step += rng.choice((-1, 1)) * 4 * sigma
        open_ = price
        close = price * math.exp(step)
        high = max(open_, close) * math.exp(abs(rng.gauss(0, 0.4 * sigma * regime)))
        low = min(open_, close) * math.exp(-abs(rng.gauss(0, 0.4 * sigma * regime)))
        bars.append(MinuteBar(start + timedelta(minutes=index), open_, high, low, close, abs(rng.gauss(10, 4))))
        price = close
    return bars


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _cache_path(asset: str, start: datetime, end: datetime):
    return settings.market_data_cache_path / "coinbase" / f"{asset}_{start:%Y%m%dT%H%M}_{end:%Y%m%dT%H%M}_1m.json"


def _read_cache(asset: str, start: datetime, end: datetime) -> list[MinuteBar] | None:
    try:
        payload = json.loads(_cache_path(asset, start, end).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if payload.get("version") != CACHE_VERSION:
        return None
    return [MinuteBar(datetime.fromtimestamp(row[0], UTC), *row[1:]) for row in payload["bars"]]


def _write_cache(asset: str, start: datetime, end: datetime, bars: list[MinuteBar]) -> None:
    path = _cache_path(asset, start, end)
    payload = {
        "version": CACHE_VERSION,
        "bars": [[int(bar.t.timestamp()), bar.open, bar.high, bar.low, bar.close, bar.volume] for bar in bars],
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False, encoding="utf-8") as handle:
            json.dump(payload, handle)
        os.replace(handle.name, path)
    except OSError:
        pass


def _get_candles(asset: str, start: datetime, end: datetime, client: httpx.Client) -> list[list[float]]:
    url = f"{settings.coinbase_base_url.rstrip('/')}/products/{asset}-USD/candles"
    try:
        response = client.get(
            url,
            params={"granularity": 60, "start": _iso(start), "end": _iso(end)},
            timeout=settings.coinbase_request_timeout_seconds,
        )
    except httpx.HTTPError as exc:
        raise MarketDataError(f"Could not reach Coinbase for {asset}: {exc.__class__.__name__}.") from exc
    if response.status_code == 429:
        raise MarketDataError("Coinbase's public rate limit was hit. Wait a few seconds and run again.", status_code=429)
    if response.status_code != 200:
        try:
            detail = str(response.json().get("message", ""))[:200]
        except ValueError:
            detail = response.text[:200]
        raise MarketDataError(f"Coinbase returned HTTP {response.status_code} for {asset}-USD: {detail}.")
    payload = response.json()
    if not isinstance(payload, list):
        raise MarketDataError(f"Coinbase returned an unexpected response for {asset}-USD.")
    return payload


def coinbase_minutes(asset: str, start: datetime, end: datetime, *, client: httpx.Client) -> list[MinuteBar]:
    """Continuous 1-minute bars over [start, end) from Coinbase, with empty minutes filled flat."""
    cached = _read_cache(asset, start, end)
    if cached is not None:
        return cached

    rows: dict[int, list[float]] = {}
    cursor = start
    while cursor < end:
        chunk_end = min(cursor + timedelta(minutes=CANDLES_PER_REQUEST), end)
        for row in _get_candles(asset, cursor, chunk_end, client):
            stamp = int(row[0])
            if int(start.timestamp()) <= stamp < int(end.timestamp()):
                rows[stamp] = row
        cursor = chunk_end

    expected = int((end - start).total_seconds() // 60)
    if len(rows) < expected * MIN_COVERAGE:
        raise MarketDataError(
            f"Coinbase returned {len(rows)} of {expected} minutes for {asset}-USD in that window; too thin to simulate.",
            status_code=422,
        )

    bars: list[MinuteBar] = []
    first = rows[min(rows)]
    last_close = float(first[3])
    for index in range(expected):
        moment = start + timedelta(minutes=index)
        row = rows.get(int(moment.timestamp()))
        if row is None:
            bars.append(MinuteBar(moment, last_close, last_close, last_close, last_close, 0.0))
            continue
        _, low, high, open_, close, volume = (float(value) for value in row[:6])
        bars.append(MinuteBar(moment, open_, high, low, close, volume))
        last_close = close

    _write_cache(asset, start, end, bars)
    return bars
