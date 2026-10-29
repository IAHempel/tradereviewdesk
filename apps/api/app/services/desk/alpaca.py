"""Alpaca Market Data: split-adjusted 5-minute stock bars, trimmed to NYSE regular-session hours.

One request covers many symbols, and the free plan allows 200 requests a minute.
Completed days use the consolidated SIP feed, which the free plan serves once
data is more than 15 minutes old.
"""

from datetime import UTC, date, datetime, time, timedelta

import httpx

from app.core.config import settings
from app.services.desk.calendar import MARKET_TIMEZONE
from app.services.desk.market import MarketDataError
from app.services.desk.slots import SlotBar, to_slot_bar

PAGE_LIMIT = 10_000
MAX_PAGES = 50


def _headers() -> dict[str, str]:
    return {
        "APCA-API-KEY-ID": settings.alpaca_api_key_id,
        "APCA-API-SECRET-KEY": settings.alpaca_api_secret_key,
    }


def _rfc3339(day: date, at: time) -> str:
    return datetime.combine(day, at, tzinfo=MARKET_TIMEZONE).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text[:200]
    return str(payload.get("message") or payload.get("error") or "")[:200]


def get_page(path: str, params: dict[str, str | int], *, client: httpx.Client, what: str) -> dict:
    """One Alpaca data request with errors mapped to messages the desk can show."""
    try:
        response = client.get(
            f"{settings.alpaca_data_base_url.rstrip('/')}{path}",
            params=params,
            headers=_headers(),
            timeout=settings.alpaca_request_timeout_seconds,
        )
    except httpx.HTTPError as exc:
        raise MarketDataError(f"Could not reach Alpaca for {what}: {exc.__class__.__name__}.") from exc

    if response.status_code == 429:
        raise MarketDataError(
            "Alpaca's rate limit was hit (200 requests a minute on the free plan). Wait a minute and run again.",
            status_code=429,
        )
    if response.status_code in (401, 403):
        raise MarketDataError(
            f"Alpaca refused the request for {what} (HTTP {response.status_code}): {_error_detail(response)}. "
            "Check ALPACA_API_KEY_ID and ALPACA_API_SECRET_KEY, and that your plan covers this feed."
        )
    if response.status_code != 200:
        raise MarketDataError(f"Alpaca returned HTTP {response.status_code} for {what}: {_error_detail(response)}.")
    return response.json()


def fetch_bars(
    symbols: list[str],
    start: date,
    end: date,
    *,
    client: httpx.Client,
    feed: str | None = None,
    end_at: datetime | None = None,
) -> dict[str, list[SlotBar]]:
    """Regular-session 5-minute bars for every symbol, from `start` through `end` (or up to `end_at`)."""
    params: dict[str, str | int] = {
        "symbols": ",".join(symbols),
        "timeframe": "5Min",
        "start": _rfc3339(start, time(0, 0)),
        "end": end_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ") if end_at else _rfc3339(end, time(20, 0)),
        "adjustment": "split",
        "feed": feed or settings.alpaca_historical_feed,
        "sort": "asc",
        "limit": PAGE_LIMIT,
    }
    bars: dict[str, list[SlotBar]] = {symbol: [] for symbol in symbols}
    what = ", ".join(symbols)

    for _ in range(MAX_PAGES):
        payload = get_page("/v2/stocks/bars", params, client=client, what=what)
        for symbol, rows in (payload.get("bars") or {}).items():
            for row in rows or []:
                bar = to_slot_bar(parse_timestamp(row["t"]), row["o"], row["h"], row["l"], row["c"], row.get("v"))
                if bar is not None and symbol in bars:
                    bars[symbol].append(bar)
        token = payload.get("next_page_token")
        if not token:
            break
        params = {**params, "page_token": token}

    return bars


def completed_bar_cutoff(now: datetime) -> datetime:
    """Bars are fetched only up to the last fully closed 5-minute interval."""
    local = now.astimezone(MARKET_TIMEZONE)
    floored = local.replace(minute=local.minute - local.minute % 5, second=0, microsecond=0)
    return floored - timedelta(seconds=1)
