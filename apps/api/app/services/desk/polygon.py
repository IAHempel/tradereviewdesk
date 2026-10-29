"""Polygon.io 5-minute aggregates, trimmed to NYSE regular-session hours."""

from datetime import UTC, date, datetime
from urllib.parse import quote

import httpx

from app.core.config import settings
from app.services.desk.market import BAR_MINUTES, MarketDataError
from app.services.desk.slots import SlotBar, to_slot_bar

AGGREGATE_LIMIT = 50_000
MAX_PAGES = 10


def _error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text[:200]
    return str(payload.get("error") or payload.get("message") or payload.get("status") or "")[:200]


def fetch_session_bars(symbol: str, start: date, end: date, *, client: httpx.Client) -> list[SlotBar]:
    """Split-adjusted 5-minute bars for `symbol` from `start` to `end` inclusive, regular session only."""
    url: str | None = (
        f"{settings.polygon_base_url.rstrip('/')}/v2/aggs/ticker/{quote(symbol, safe='')}"
        f"/range/{BAR_MINUTES}/minute/{start.isoformat()}/{end.isoformat()}"
    )
    params: dict[str, str | int] | None = {"adjusted": "true", "sort": "asc", "limit": AGGREGATE_LIMIT}
    bars: list[SlotBar] = []

    for _ in range(MAX_PAGES):
        if url is None:
            break
        try:
            response = client.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {settings.polygon_api_key}"},
                timeout=settings.polygon_request_timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise MarketDataError(f"Could not reach Polygon for {symbol}: {exc.__class__.__name__}.") from exc

        if response.status_code == 429:
            raise MarketDataError(
                "Polygon's rate limit was hit (the free plan allows 5 requests a minute, one per symbol). "
                "Symbols already loaded are cached, so wait a minute and run again.",
                status_code=429,
            )
        if response.status_code in (401, 403):
            raise MarketDataError(
                f"Polygon refused the request for {symbol} (HTTP {response.status_code}): {_error_detail(response)}. "
                "Check POLYGON_API_KEY and that your plan covers these dates."
            )
        if response.status_code != 200:
            raise MarketDataError(f"Polygon returned HTTP {response.status_code} for {symbol}: {_error_detail(response)}.")

        payload = response.json()
        if payload.get("status") in ("ERROR", "NOT_AUTHORIZED"):
            raise MarketDataError(f"Polygon could not serve {symbol}: {_error_detail(response)}.")

        for row in payload.get("results") or []:
            stamp = datetime.fromtimestamp(row["t"] / 1000, tz=UTC)
            bar = to_slot_bar(stamp, row["o"], row["h"], row["l"], row["c"], row.get("v"))
            if bar is not None:
                bars.append(bar)

        # next_url already carries the query and cursor; only auth is re-sent.
        url = payload.get("next_url")
        params = None

    return bars


def fetch_bars(symbols: list[str], start: date, end: date, *, client: httpx.Client) -> dict[str, list[SlotBar]]:
    """Polygon serves one ticker per request, so callers batch one symbol at a time."""
    return {symbol: fetch_session_bars(symbol, start, end, client=client) for symbol in symbols}
