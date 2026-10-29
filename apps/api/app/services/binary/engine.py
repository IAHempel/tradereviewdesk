"""Two-sided quoting on simulated 15-minute crypto Up/Down binaries.

Each 15-minute window pays $1 per Up share if the asset closes at or above its
open, else $1 per Down share. The desk keeps a fair probability from the real
(or synthetic) underlying, posts a small grid of bids on both sides so a filled
Up+Down pair costs less than the $1 it is guaranteed to pay, and shades both
sides against the inventory it already holds.

The market it trades against is a model: the crowd's price is the same fair
value seen `crowd_lag_minutes` late plus mean-reverting noise. A resting bid
fills only when the crowd's traded price goes through it during the minute, and
then only with the queue probability. Every run is repeated against an
efficient crowd (no lag, no noise) so the share of P&L that comes from those
assumptions is visible.
"""

import math
import random
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import httpx

from app.schemas.binary import (
    BinaryAssetSeries,
    BinaryBaseline,
    BinaryConfig,
    BinaryFill,
    BinaryMinute,
    BinaryRunResponse,
    BinarySummary,
    BinaryWindow,
)
from app.services.binary.market import MinuteBar, coinbase_minutes, synthetic_minutes
from app.services.desk.market import MarketDataError
from app.services.desk.stats import max_drawdown_pct, run_monte_carlo

WINDOW_MINUTES = 15
WARMUP_MINUTES = 60
EWMA_LAMBDA = 0.94
MIN_PRICE = 0.01
MAX_PRICE = 0.99
TICK = 0.001
MAX_FILLS_RETURNED = 600


def _phi(value: float) -> float:
    return 0.5 * (1 + math.erf(value / math.sqrt(2)))


def _clip(value: float, low: float = MIN_PRICE, high: float = MAX_PRICE) -> float:
    return max(low, min(high, value))


def probability_up(price: float, window_open: float, sigma: float, minutes_left: float) -> float:
    """P(close >= open) for a driftless random walk with per-minute volatility `sigma`."""
    if minutes_left <= 0:
        return 1.0 if price >= window_open else 0.0
    return _phi(math.log(price / window_open) / (max(sigma, 1e-6) * math.sqrt(minutes_left)))


@dataclass(frozen=True)
class CrowdModel:
    lag_minutes: int
    noise: float
    half_life_minutes: float
    spread: float

    @property
    def decay(self) -> float:
        return math.exp(math.log(0.5) / self.half_life_minutes)


@dataclass
class Order:
    side: str
    price: float
    shares: float
    level: int


@dataclass
class WindowBook:
    up_shares: float = 0.0
    down_shares: float = 0.0
    up_cost: float = 0.0
    down_cost: float = 0.0
    fees: float = 0.0
    fills: int = 0

    def value_at(self, fair_up: float) -> float:
        return self.up_shares * fair_up + self.down_shares * (1 - fair_up) - self.up_cost - self.down_cost - self.fees


@dataclass
class SimResult:
    contributions: list[float]
    fill_counts: list[int]
    inventory: dict[str, list[float]]
    windows: list[BinaryWindow] = field(default_factory=list)
    fills: list[BinaryFill] = field(default_factory=list)
    series: list[BinaryAssetSeries] = field(default_factory=list)
    fill_arrival: list[int] = field(default_factory=lambda: [0] * WINDOW_MINUTES)
    dislocations: list[tuple[float, float]] = field(default_factory=list)


def _initial_variance(bars: list[MinuteBar]) -> float:
    returns = [math.log(b.close / a.close) for a, b in zip(bars, bars[1:]) if a.close > 0 and b.close > 0]
    if not returns:
        return 1e-8
    return max(sum(value * value for value in returns) / len(returns), 1e-10)


def simulate(
    config: BinaryConfig,
    bars_by_asset: dict[str, list[MinuteBar]],
    start: datetime,
    crowd: CrowdModel,
    seed: int,
    *,
    record: bool,
) -> SimResult:
    total_minutes = config.hours * 60
    result = SimResult(
        contributions=[0.0] * total_minutes,
        fill_counts=[0] * total_minutes,
        inventory={asset: [0.0] * total_minutes for asset in bars_by_asset},
    )
    for asset, bars in bars_by_asset.items():
        _simulate_asset(config, asset, bars, start, crowd, seed, result, record=record)
    return result


def _simulate_asset(
    config: BinaryConfig,
    asset: str,
    bars: list[MinuteBar],
    start: datetime,
    crowd: CrowdModel,
    seed: int,
    result: SimResult,
    *,
    record: bool,
) -> None:
    total_minutes = config.hours * 60
    half_spread = config.half_spread_cents / 100
    step = config.level_step_cents / 100
    skew = config.inventory_skew_cents / 100
    fee_rate = config.maker_fee_bps / 10_000
    fill_rng = random.Random(f"{seed}-{asset}-fills")
    crowd_rng = random.Random(f"{seed}-{asset}-crowd")
    variance = _initial_variance(bars[:WARMUP_MINUTES])
    realized = 0.0
    dislocation = 0.0
    prices: list[float] = []
    fairs: list[float] = []
    crowds: list[float] = []
    bids_up: list[float | None] = []
    bids_down: list[float | None] = []

    def check_fills(book: WindowBook, resting: list[Order], path: tuple[float, float], minute: int, window_index: int) -> None:
        """Fills resting bids the crowd traded through during `minute`, each with the queue probability."""
        up_low = min(path) - crowd.spread / 2 - abs(crowd_rng.gauss(0, crowd.noise / 2))
        down_low = min(1 - path[0], 1 - path[1]) - crowd.spread / 2 - abs(crowd_rng.gauss(0, crowd.noise / 2))
        for order in resting:
            low = up_low if order.side == "up" else down_low
            if low > order.price - TICK or fill_rng.random() > config.queue_fill_probability:
                continue
            cost = order.price * order.shares
            if order.side == "up":
                book.up_shares += order.shares
                book.up_cost += cost
            else:
                book.down_shares += order.shares
                book.down_cost += cost
            book.fees += cost * fee_rate
            book.fills += 1
            result.fill_counts[minute] += 1
            result.fill_arrival[minute % WINDOW_MINUTES] += 1
            if record:
                result.fills.append(
                    BinaryFill(
                        t=(start + timedelta(minutes=minute, seconds=30)).isoformat(),
                        minute=minute,
                        asset=asset,
                        window_index=window_index,
                        side=order.side,
                        price=round(order.price, 3),
                        shares=order.shares,
                        level=order.level,
                        fair_up=round(fairs[minute], 4),
                        crowd_up=round(path[0], 4),
                    )
                )

    for window_index in range(total_minutes // WINDOW_MINUTES):
        book = WindowBook()
        first = WARMUP_MINUTES + window_index * WINDOW_MINUTES
        window_open = bars[first].open
        resting: list[Order] = []
        crowd_previous: float | None = None
        last_mark = 0.0

        for minute_in_window in range(WINDOW_MINUTES):
            minute = window_index * WINDOW_MINUTES + minute_in_window
            index = WARMUP_MINUTES + minute
            bar = bars[index]
            completed = math.log(bars[index - 1].close / bars[index - 2].close)
            variance = EWMA_LAMBDA * variance + (1 - EWMA_LAMBDA) * completed * completed
            sigma = math.sqrt(variance)
            minutes_left = WINDOW_MINUTES - minute_in_window
            fair_up = probability_up(bar.open, window_open, sigma, minutes_left)

            # The crowd sees the price `lag` minutes late, plus noise that decays with the configured half-life.
            lagged = bars[index - crowd.lag_minutes].open
            crowd_fair = probability_up(lagged, window_open, sigma, minutes_left + crowd.lag_minutes)
            dislocation = dislocation * crowd.decay + crowd_rng.gauss(0, crowd.noise * math.sqrt(1 - crowd.decay**2))
            crowd_up = _clip(crowd_fair + dislocation, 0.02, 0.98)
            result.dislocations.append((minute_in_window, crowd_up - fair_up))

            prices.append(round(bar.open, 6))
            fairs.append(round(fair_up, 4))
            crowds.append(round(crowd_up, 4))
            if resting and crowd_previous is not None:
                check_fills(book, resting, (crowd_previous, crowd_up), minute - 1, window_index)

            resting = []
            if minutes_left > config.stop_quoting_minutes:
                reservation = fair_up - skew * (book.up_shares - book.down_shares) / config.max_shares_per_side
                for level in range(config.levels):
                    room = config.shares_per_level * (level + 1)
                    up_price = round(min(reservation - half_spread - level * step, MAX_PRICE), 3)
                    down_price = round(min(1 - reservation - half_spread - level * step, MAX_PRICE), 3)
                    # A bid that would sit under the minimum tick is skipped, never rounded up past fair value.
                    if up_price >= MIN_PRICE and book.up_shares + room <= config.max_shares_per_side:
                        resting.append(Order("up", up_price, config.shares_per_level, level))
                    if down_price >= MIN_PRICE and book.down_shares + room <= config.max_shares_per_side:
                        resting.append(Order("down", down_price, config.shares_per_level, level))
            crowd_previous = crowd_up
            bids_up.append(next((order.price for order in resting if order.side == "up" and order.level == 0), None))
            bids_down.append(next((order.price for order in resting if order.side == "down" and order.level == 0), None))

            last_mark = realized + book.value_at(fair_up)
            result.contributions[minute] += last_mark
            result.inventory[asset][minute] = book.up_shares - book.down_shares

        final_minute = window_index * WINDOW_MINUTES + WINDOW_MINUTES - 1
        last = bars[first + WINDOW_MINUTES - 1]
        outcome_up = last.close >= window_open
        if resting and crowd_previous is not None:
            check_fills(book, resting, (crowd_previous, 1.0 if outcome_up else 0.0), final_minute, window_index)

        pnl = (book.up_shares if outcome_up else book.down_shares) - book.up_cost - book.down_cost - book.fees
        realized += pnl
        # The window resolves at the end of its last minute, so that minute's equity is the realized total.
        result.contributions[final_minute] += realized - last_mark
        result.inventory[asset][final_minute] = book.up_shares - book.down_shares

        pairs = min(book.up_shares, book.down_shares)
        unpaired = abs(book.up_shares - book.down_shares)
        result.windows.append(
            BinaryWindow(
                asset=asset,
                index=window_index,
                start=(start + timedelta(minutes=window_index * WINDOW_MINUTES)).isoformat(),
                end=(start + timedelta(minutes=(window_index + 1) * WINDOW_MINUTES)).isoformat(),
                start_minute=window_index * WINDOW_MINUTES,
                open=round(window_open, 6),
                close=round(last.close, 6),
                outcome="up" if outcome_up else "down",
                up_shares=book.up_shares,
                down_shares=book.down_shares,
                up_cost=round(book.up_cost, 4),
                down_cost=round(book.down_cost, 4),
                pairs=pairs,
                avg_pair_cost=(
                    round(book.up_cost / book.up_shares + book.down_cost / book.down_shares, 4) if pairs > 0 else None
                ),
                unpaired_side=None if unpaired == 0 else ("up" if book.up_shares > book.down_shares else "down"),
                unpaired_shares=unpaired,
                fees=round(book.fees, 4),
                pnl=round(pnl, 4),
                fills=book.fills,
            )
        )

    if record:
        result.series.append(
            BinaryAssetSeries(asset=asset, price=prices, fair_up=fairs, crowd_up=crowds, bid_up=bids_up, bid_down=bids_down)
        )


def _floor_to_window(moment: datetime) -> datetime:
    moment = moment.astimezone(UTC).replace(second=0, microsecond=0)
    return moment - timedelta(minutes=moment.minute % WINDOW_MINUTES)


def resolve_config(config: BinaryConfig, now: datetime) -> BinaryConfig:
    """Fills in the seed and the end of the last completed 15-minute window."""
    latest_complete = _floor_to_window(now - timedelta(minutes=2))
    end = _floor_to_window(config.end_at) if config.end_at else latest_complete
    return config.model_copy(update={"seed": config.seed if config.seed is not None else secrets.randbelow(2**31), "end_at": end})


def _load_bars(
    config: BinaryConfig, warm_start: datetime, end: datetime, client: httpx.Client | None
) -> tuple[dict[str, list[MinuteBar]], list[str]]:
    minutes = int((end - warm_start).total_seconds() // 60)
    if config.data_source == "synthetic":
        return {asset: synthetic_minutes(asset, warm_start, minutes, config.seed or 0) for asset in config.assets}, []

    owns_client = client is None
    http = client or httpx.Client()
    bars: dict[str, list[MinuteBar]] = {}
    notes: list[str] = []
    try:
        for asset in config.assets:
            try:
                bars[asset] = coinbase_minutes(asset, warm_start, end, client=http)
            except MarketDataError as exc:
                if exc.status_code == 429 or len(config.assets) == 1:
                    raise
                notes.append(f"Dropped {asset}: {exc.message}")
    finally:
        if owns_client:
            http.close()
    if not bars:
        raise MarketDataError("None of the assets had enough Coinbase candles for that window.", status_code=422)
    return bars, notes


def _half_life(dislocations: list[tuple[float, float]]) -> float | None:
    """AR(1) half-life of crowd minus fair, from consecutive minutes inside each window."""
    numerator = denominator = 0.0
    for (minute_a, value_a), (minute_b, value_b) in zip(dislocations, dislocations[1:]):
        if minute_b == minute_a + 1:
            numerator += value_a * value_b
            denominator += value_a * value_a
    if denominator <= 0:
        return None
    phi = numerator / denominator
    if not 0 < phi < 1:
        return None
    return round(math.log(0.5) / math.log(phi), 2)


def _summarize(config: BinaryConfig, windows: list[BinaryWindow], equity: list[float]) -> BinarySummary:
    fills = sum(window.fills for window in windows)
    pairs = sum(window.pairs for window in windows)
    shares = sum(window.up_shares + window.down_shares for window in windows)
    paired_cost = sum(window.pairs * window.avg_pair_cost for window in windows if window.avg_pair_cost is not None)
    paired_pnl = sum(window.pairs * (1 - window.avg_pair_cost) for window in windows if window.avg_pair_cost is not None)
    fees = sum(window.fees for window in windows)
    net = sum(window.pnl for window in windows)
    won = sum(1 for window in windows if window.pnl > 0)
    traded = [window for window in windows if window.fills]
    return BinarySummary(
        starting_balance=config.starting_balance,
        ending_balance=round(config.starting_balance + net, 2),
        net_pnl=round(net, 2),
        return_pct=round(net / config.starting_balance * 100, 2),
        windows=len(windows),
        windows_won=won,
        window_win_rate=round(won / len(traded), 3) if traded else None,
        fills=fills,
        fills_per_hour=round(fills / config.hours, 1),
        pairs_locked=pairs,
        paired_share_pct=round(2 * pairs / shares * 100, 1) if shares else None,
        avg_pair_cost=round(paired_cost / pairs, 4) if pairs else None,
        paired_pnl=round(paired_pnl, 2),
        unpaired_pnl=round(net + fees - paired_pnl, 2),
        fees=round(fees, 2),
        max_drawdown_pct=max_drawdown_pct(equity, config.starting_balance),
    )


def run_binary(config: BinaryConfig, *, client: httpx.Client | None = None, now: datetime | None = None) -> BinaryRunResponse:
    now = now or datetime.now(UTC)
    resolved = resolve_config(config, now)
    end = resolved.end_at
    assert end is not None
    if resolved.data_source == "coinbase" and end > now:
        raise MarketDataError("Pick an end time in the past; only completed windows can be simulated.", status_code=422)
    start = end - timedelta(hours=resolved.hours)
    bars, notes = _load_bars(resolved, start - timedelta(minutes=WARMUP_MINUTES), end, client)
    resolved = resolved.model_copy(update={"assets": [asset for asset in resolved.assets if asset in bars]})

    crowd = CrowdModel(
        lag_minutes=resolved.crowd_lag_minutes,
        noise=resolved.crowd_noise_cents / 100,
        half_life_minutes=resolved.dislocation_half_life_minutes,
        spread=resolved.crowd_spread_cents / 100,
    )
    efficient = CrowdModel(lag_minutes=0, noise=0.0, half_life_minutes=resolved.dislocation_half_life_minutes, spread=crowd.spread)
    seed = resolved.seed or 0
    main = simulate(resolved, bars, start, crowd, seed, record=True)
    baseline = simulate(resolved, bars, start, efficient, seed, record=False)

    equity = [resolved.starting_balance + value for value in main.contributions]
    summary = _summarize(resolved, main.windows, equity)
    baseline_summary = _summarize(resolved, baseline.windows, [resolved.starting_balance + value for value in baseline.contributions])

    ordered = sorted(main.windows, key=lambda window: (window.start, window.asset))
    balance = resolved.starting_balance
    window_returns = []
    for window in ordered:
        if window.fills:
            window_returns.append(window.pnl / balance)
        balance += window.pnl

    return BinaryRunResponse(
        id="pending",
        created_at="",
        data_source=resolved.data_source,
        config=resolved,
        summary=summary,
        baseline=BinaryBaseline(
            net_pnl=baseline_summary.net_pnl,
            fills=baseline_summary.fills,
            pairs_locked=baseline_summary.pairs_locked,
            window_win_rate=baseline_summary.window_win_rate,
        ),
        minutes=[
            BinaryMinute(
                t=(start + timedelta(minutes=minute)).isoformat(),
                equity=round(equity[minute], 2),
                fills=main.fill_counts[minute],
                inventory={asset: values[minute] for asset, values in main.inventory.items()},
            )
            for minute in range(len(equity))
        ],
        series=main.series,
        windows=main.windows,
        fills=sorted(main.fills, key=lambda fill: (fill.minute, fill.asset))[-MAX_FILLS_RETURNED:],
        fill_arrival=main.fill_arrival,
        dislocation_half_life_minutes=_half_life(main.dislocations),
        monte_carlo=run_monte_carlo(window_returns, seed=seed),
        notes=notes,
    )
