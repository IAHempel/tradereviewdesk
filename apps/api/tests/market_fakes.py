"""Fake market-data providers for tests, shaped like the providers' documented responses."""

import math
import random
from datetime import UTC, date, datetime, timedelta
from urllib.parse import urlparse

import httpx

from app.services.desk.calendar import MARKET_TIMEZONE

# Thanksgiving week 2025: Thursday Nov 27 is a holiday and Friday Nov 28 closes at 1:00 pm.
END_DATE = date(2025, 11, 28)
HOLIDAYS = {date(2025, 11, 27)}


def minute_rows(symbol: str, start: date, end: date, *, coverage: float = 1.0) -> list[dict]:
    """5-minute rows shaped like Polygon's /v2/aggs results (epoch-ms `t`), extended hours included."""
    rng = random.Random(symbol)
    price = 100 + rng.random() * 300
    rows = []
    day = start
    while day <= end:
        if day.weekday() < 5 and day not in HOLIDAYS:
            for minute in range(4 * 60, 20 * 60, 5):
                if rng.random() > coverage:
                    continue
                stamp = datetime(day.year, day.month, day.day, minute // 60, minute % 60, tzinfo=MARKET_TIMEZONE)
                open_ = price
                price *= math.exp(rng.gauss(0, 0.002))
                rows.append(
                    {
                        "t": int(stamp.timestamp() * 1000),
                        "o": round(open_, 2),
                        "h": round(max(open_, price) * 1.001, 2),
                        "l": round(min(open_, price) * 0.999, 2),
                        "c": round(price, 2),
                        "v": rng.randint(1_000, 90_000),
                        "vw": round(price, 2),
                        "n": rng.randint(10, 500),
                    }
                )
        day += timedelta(days=1)
    return rows


class FakePolygon:
    """Serves aggregate requests from generated rows and records what was asked."""

    def __init__(self, *, coverage: dict[str, float] | None = None, page_size: int | None = None) -> None:
        self.coverage = coverage or {}
        self.page_size = page_size
        self.requests: list[httpx.Request] = []
        self.status_override: tuple[int, dict] | None = None

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.status_override:
            status, body = self.status_override
            return httpx.Response(status, json=body)

        parts = urlparse(str(request.url)).path.split("/")
        symbol, start, end = parts[4], date.fromisoformat(parts[8]), date.fromisoformat(parts[9])
        rows = minute_rows(symbol, start, end, coverage=self.coverage.get(symbol, 1.0))
        offset = int(request.url.params.get("cursor", 0))
        page = rows[offset : offset + self.page_size] if self.page_size else rows
        body = {"ticker": symbol, "status": "OK", "resultsCount": len(page), "results": page}
        if self.page_size and offset + self.page_size < len(rows):
            body["next_url"] = f"{str(request.url).split('?')[0]}?cursor={offset + self.page_size}"
        return httpx.Response(200, json=body)

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handler))


def _parse_rfc3339(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class FakeAlpaca:
    """Serves /v2/stocks/bars and /v2/stocks/trades (multi-symbol, page tokens) and records requests."""

    def __init__(self, *, coverage: dict[str, float] | None = None, page_size: int | None = None) -> None:
        self.coverage = coverage or {}
        self.page_size = page_size
        self.requests: list[httpx.Request] = []
        self.status_override: tuple[int, dict] | None = None
        self.trades_status: tuple[int, dict] | None = None
        self.posts: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            # Notification webhooks share the client in live mode; record them separately.
            self.posts.append(request)
            return httpx.Response(200)
        self.requests.append(request)
        if self.status_override:
            status, body = self.status_override
            return httpx.Response(status, json=body)
        if request.url.path == "/v2/stocks/trades":
            return self._trades(request)

        params = request.url.params
        start, end = _parse_rfc3339(params["start"]), _parse_rfc3339(params["end"])
        start_day = start.astimezone(MARKET_TIMEZONE).date()
        end_day = end.astimezone(MARKET_TIMEZONE).date()
        flat = []
        for symbol in sorted(params["symbols"].split(",")):
            for row in minute_rows(symbol, start_day, end_day, coverage=self.coverage.get(symbol, 1.0)):
                stamp = datetime.fromtimestamp(row["t"] / 1000, tz=UTC)
                if start <= stamp <= end:
                    flat.append((symbol, {**row, "t": stamp.strftime("%Y-%m-%dT%H:%M:%SZ")}))

        offset = int(params.get("page_token") or 0)
        page = flat[offset : offset + self.page_size] if self.page_size else flat
        bars: dict[str, list[dict]] = {}
        for symbol, row in page:
            bars.setdefault(symbol, []).append(row)
        next_token = str(offset + self.page_size) if self.page_size and offset + self.page_size < len(flat) else None
        return httpx.Response(200, json={"bars": bars, "next_page_token": next_token})

    def _trades(self, request: httpx.Request) -> httpx.Response:
        """Trade prints (nanosecond timestamps, like Alpaca) with a buying bias in the first hour."""
        if self.trades_status:
            status, body = self.trades_status
            return httpx.Response(status, json=body)
        params = request.url.params
        start, end = _parse_rfc3339(params["start"]), _parse_rfc3339(params["end"])
        flat = []
        for symbol in sorted(params["symbols"].split(",")):
            rng = random.Random(f"{symbol}-{start.date()}")
            price = 100 + rng.random() * 300
            stamp = start
            while stamp < end:
                drift = 0.0004 if stamp - start < timedelta(hours=1) else 0.0
                price *= math.exp(rng.gauss(drift, 0.0006))
                text = stamp.strftime("%Y-%m-%dT%H:%M:%S") + f".{rng.randint(0, 999_999_999):09d}Z"
                flat.append((symbol, {"t": text, "x": "V", "p": round(price, 2), "s": rng.randint(1, 300), "c": ["@"], "z": "C"}))
                stamp += timedelta(seconds=rng.randint(20, 90))

        offset = int(params.get("page_token") or 0)
        page = flat[offset : offset + self.page_size] if self.page_size else flat
        trades: dict[str, list[dict]] = {}
        for symbol, row in page:
            trades.setdefault(symbol, []).append(row)
        next_token = str(offset + self.page_size) if self.page_size and offset + self.page_size < len(flat) else None
        return httpx.Response(200, json={"trades": trades, "next_page_token": next_token})

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handler))
