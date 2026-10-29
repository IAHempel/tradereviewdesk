"""The six desk agents: Scout, Filter, Analyst, Risk, Executor, Logger.

Each agent owns one decision and records a reason for it. None of them can see
a bar before it closes: setups are detected on a closed bar and filled at the
next bar's open, and stops are only ever tightened.
"""

from dataclasses import dataclass, field
from statistics import fmean, pstdev

from app.schemas.desk import (
    DeskAgent,
    DeskConfig,
    DeskEvent,
    DeskExitReason,
    DeskPipelineCounts,
    DeskSetup,
    DeskSide,
)
from app.services.desk.market import Bar

LOOKBACK = 20
FAST_EMA = 9
SLOW_EMA = 21
ATR_PERIOD = 14
OPENING_NOISE_BARS = 2
CLOSING_BELL_BARS = 6
TILT_COOLDOWN_BARS = 12
# Continuation setups need buyers (or sellers) behind them; reversal setups trade against flow by design.
FLOW_CONFIRMED_SETUPS = ("breakout", "trend_pullback")

# Starting assumptions for each setup's win rate and how many pseudo-trades of
# weight they carry. The Analyst updates them with journal and live outcomes.
SETUP_PRIORS: dict[DeskSetup, tuple[float, float]] = {
    "breakout": (0.38, 12),
    "sweep_reclaim": (0.45, 12),
    "trend_pullback": (0.42, 12),
    "mean_reversion": (0.55, 12),
}
SETUP_LABELS: dict[DeskSetup, str] = {
    "breakout": "Breakout",
    "sweep_reclaim": "Sweep reclaim",
    "trend_pullback": "Trend pullback",
    "mean_reversion": "Mean reversion",
}
JOURNAL_TAG_KEYWORDS: dict[DeskSetup, tuple[str, ...]] = {
    "breakout": ("breakout", "opening-range", "orb", "range-break"),
    "sweep_reclaim": ("reclaim", "sweep", "failed-breakdown", "stop-run"),
    "trend_pullback": ("pullback", "trend", "continuation", "flag"),
    "mean_reversion": ("reversion", "fade", "overextended", "snapback"),
}
JOURNAL_PRIOR_CAP = 20

KILL_LABELS: dict[str, str] = {
    "setup_disabled": "Setup not enabled",
    "opening_noise": "Opening noise window",
    "closing_bell": "Too close to the bell",
    "daily_loss_halt": "Daily loss limit hit",
    "tilt_cooldown": "Loss-streak cooldown",
    "symbol_busy": "Symbol already working",
    "max_open": "Max open positions",
    "stop_too_tight": "Stop inside noise",
    "stop_too_wide": "Stop too wide",
    "reward_risk": "Reward:risk below minimum",
    "score": "Score below minimum",
    "negative_ev": "Non-positive expected value",
    "kelly": "Kelly says no edge",
    "buying_power": "No buying power left",
    "flow_against": "Order flow against the trade",
    "gap_stop": "Gapped through stop",
    "gap_target": "Gapped past target",
}


@dataclass
class SymbolTape:
    symbol: str
    bars: list[Bar] = field(default_factory=list)
    ema_fast: list[float] = field(default_factory=list)
    ema_slow: list[float] = field(default_factory=list)
    true_ranges: list[float] = field(default_factory=list)

    def append(self, bar: Bar) -> None:
        previous_close = self.bars[-1].close if self.bars else bar.open
        self.true_ranges.append(max(bar.high - bar.low, abs(bar.high - previous_close), abs(bar.low - previous_close)))
        self.ema_fast.append(_next_ema(self.ema_fast, bar.close, FAST_EMA))
        self.ema_slow.append(_next_ema(self.ema_slow, bar.close, SLOW_EMA))
        self.bars.append(bar)

    @property
    def last(self) -> Bar:
        return self.bars[-1]

    def prior(self, count: int) -> list[Bar]:
        return self.bars[-count - 1 : -1]

    def atr(self) -> float:
        window = self.true_ranges[-ATR_PERIOD:]
        return max(fmean(window), 0.01)

    def ready(self) -> bool:
        return len(self.bars) > LOOKBACK + 10


def _next_ema(series: list[float], value: float, period: int) -> float:
    if not series:
        return value
    alpha = 2 / (period + 1)
    return series[-1] + alpha * (value - series[-1])


@dataclass
class Setup:
    symbol: str
    setup: DeskSetup
    side: DeskSide
    entry: float
    stop: float
    target: float
    atr: float
    volume_ratio: float
    trend_aligned: bool
    thesis: str

    @property
    def risk_per_unit(self) -> float:
        return abs(self.entry - self.stop)

    @property
    def reward_risk(self) -> float:
        if self.risk_per_unit <= 0:
            return 0.0
        return abs(self.target - self.entry) / self.risk_per_unit

    @property
    def stop_atr(self) -> float:
        return self.risk_per_unit / self.atr

    @property
    def direction(self) -> int:
        return 1 if self.side == "long" else -1


class ScoutAgent:
    """Scans each closed bar for the four setup shapes the desk knows."""

    def scan(self, tape: SymbolTape) -> list[Setup]:
        if not tape.ready():
            return []

        bar = tape.last
        prior = tape.prior(LOOKBACK)
        atr = tape.atr()
        prior_high = max(item.high for item in prior)
        prior_low = min(item.low for item in prior)
        volume_ratio = bar.volume / max(fmean(item.volume for item in prior), 1.0)
        trending_up = tape.ema_fast[-1] > tape.ema_slow[-1]

        setups: list[Setup] = []

        if bar.close > prior_high and volume_ratio >= 1.3:
            stop = min(prior_high - 0.25 * atr, bar.close - 0.6 * atr)
            setups.append(
                Setup(
                    tape.symbol, "breakout", "long", bar.close, stop, bar.close + 2.5 * (bar.close - stop),
                    atr, volume_ratio, trending_up,
                    f"Closed above the {LOOKBACK}-bar high {prior_high:.2f} on {volume_ratio:.1f}x volume",
                )
            )
        elif bar.close < prior_low and volume_ratio >= 1.3:
            stop = max(prior_low + 0.25 * atr, bar.close + 0.6 * atr)
            setups.append(
                Setup(
                    tape.symbol, "breakout", "short", bar.close, stop, bar.close - 2.5 * (stop - bar.close),
                    atr, volume_ratio, not trending_up,
                    f"Closed below the {LOOKBACK}-bar low {prior_low:.2f} on {volume_ratio:.1f}x volume",
                )
            )

        midpoint = (prior_high + prior_low) / 2
        if bar.low < prior_low < bar.close and bar.close > bar.open and midpoint > bar.close:
            setups.append(
                Setup(
                    tape.symbol, "sweep_reclaim", "long", bar.close, bar.low - 0.1 * atr, midpoint,
                    atr, volume_ratio, trending_up,
                    f"Swept the {LOOKBACK}-bar low {prior_low:.2f} and closed back inside the range",
                )
            )
        elif bar.high > prior_high > bar.close and bar.close < bar.open and midpoint < bar.close:
            setups.append(
                Setup(
                    tape.symbol, "sweep_reclaim", "short", bar.close, bar.high + 0.1 * atr, midpoint,
                    atr, volume_ratio, not trending_up,
                    f"Swept the {LOOKBACK}-bar high {prior_high:.2f} and closed back inside the range",
                )
            )

        fast, slow, slow_before = tape.ema_fast[-1], tape.ema_slow[-1], tape.ema_slow[-6]
        if fast > slow > slow_before and bar.low <= slow + 0.1 * atr and bar.close > fast and bar.close > bar.open:
            stop = min(bar.low, slow) - 0.3 * atr
            setups.append(
                Setup(
                    tape.symbol, "trend_pullback", "long", bar.close, stop, bar.close + 2 * (bar.close - stop),
                    atr, volume_ratio, True,
                    f"Pulled back into the rising {SLOW_EMA} EMA and closed back above the {FAST_EMA} EMA",
                )
            )
        elif fast < slow < slow_before and bar.high >= slow - 0.1 * atr and bar.close < fast and bar.close < bar.open:
            stop = max(bar.high, slow) + 0.3 * atr
            setups.append(
                Setup(
                    tape.symbol, "trend_pullback", "short", bar.close, stop, bar.close - 2 * (stop - bar.close),
                    atr, volume_ratio, True,
                    f"Rallied into the falling {SLOW_EMA} EMA and closed back below the {FAST_EMA} EMA",
                )
            )

        closes = [item.close for item in tape.bars[-LOOKBACK:]]
        mean, deviation = fmean(closes), pstdev(closes)
        slope = (tape.ema_slow[-1] - tape.ema_slow[-11]) / 10 / atr
        if deviation > 0 and abs(slope) < 0.08:
            z_score = (bar.close - mean) / deviation
            if z_score < -2.2:
                setups.append(
                    Setup(
                        tape.symbol, "mean_reversion", "long", bar.close, bar.low - 0.5 * atr, mean,
                        atr, volume_ratio, True,
                        f"Stretched {abs(z_score):.1f} deviations below a flat {LOOKBACK}-bar mean",
                    )
                )
            elif z_score > 2.2:
                setups.append(
                    Setup(
                        tape.symbol, "mean_reversion", "short", bar.close, bar.high + 0.5 * atr, mean,
                        atr, volume_ratio, True,
                        f"Stretched {z_score:.1f} deviations above a flat {LOOKBACK}-bar mean",
                    )
                )

        return setups


@dataclass
class DeskGate:
    """What the Filter needs to know about the desk at the moment a setup arrives."""

    bar_index: int
    session_length: int
    halted: bool
    cooldown_until: int
    step: int
    busy_symbols: set[str]
    working_count: int
    flow: float = 0.0


class FilterAgent:
    """Applies the user's hard rules. Anything that fails is killed with a reason."""

    def __init__(self, config: DeskConfig) -> None:
        self.config = config

    def review(self, setup: Setup, gate: DeskGate) -> str | None:
        if setup.setup not in self.config.allowed_setups:
            return "setup_disabled"
        if gate.bar_index < OPENING_NOISE_BARS:
            return "opening_noise"
        if gate.bar_index >= gate.session_length - CLOSING_BELL_BARS:
            return "closing_bell"
        if gate.halted:
            return "daily_loss_halt"
        if gate.step < gate.cooldown_until:
            return "tilt_cooldown"
        if setup.symbol in gate.busy_symbols:
            return "symbol_busy"
        if gate.working_count >= self.config.max_open_positions:
            return "max_open"
        if setup.stop_atr < 0.25:
            return "stop_too_tight"
        if setup.stop_atr > 3.0:
            return "stop_too_wide"
        if setup.reward_risk < self.config.min_reward_risk:
            return "reward_risk"
        if setup.setup in FLOW_CONFIRMED_SETUPS and setup.direction * gate.flow <= -self.config.flow_veto:
            return "flow_against"
        return None


@dataclass
class Assessment:
    score: int
    win_probability: float
    expected_r: float


class AnalystAgent:
    """Scores setups and keeps a Beta posterior on each setup's win rate."""

    def __init__(self, config: DeskConfig, journal_counts: dict[DeskSetup, tuple[int, int]]) -> None:
        self.config = config
        self.journal_counts = journal_counts
        self.live_counts: dict[DeskSetup, list[int]] = {setup: [0, 0] for setup in SETUP_PRIORS}

    def prior_counts(self, setup: DeskSetup) -> tuple[float, float]:
        rate, weight = SETUP_PRIORS[setup]
        return rate * weight, (1 - rate) * weight

    def posterior(self, setup: DeskSetup) -> float:
        prior_wins, prior_losses = self.prior_counts(setup)
        journal_wins, journal_losses = self.journal_counts.get(setup, (0, 0))
        live_wins, live_losses = self.live_counts[setup]
        wins = prior_wins + journal_wins + live_wins
        losses = prior_losses + journal_losses + live_losses
        return wins / (wins + losses)

    def record_outcome(self, setup: DeskSetup, won: bool) -> None:
        self.live_counts[setup][0 if won else 1] += 1

    def assess(self, setup: Setup, flow: float = 0.0) -> Assessment:
        win_probability = self.posterior(setup.setup)
        reward_risk = setup.reward_risk
        expected_r = win_probability * reward_risk - (1 - win_probability)

        edge_points = _clamp(expected_r / 0.5) * 30
        trend_points = 15 if setup.trend_aligned else 0
        volume_points = _clamp(setup.volume_ratio - 1.0) * 10
        flow_points = _clamp((setup.direction * flow + 0.1) / 0.5) * 15
        reward_points = _clamp((reward_risk - 1) / 2) * 15
        stop_points = 15 if 0.5 <= setup.stop_atr <= 2.0 else 7
        score = round(edge_points + trend_points + volume_points + flow_points + reward_points + stop_points)

        return Assessment(score=score, win_probability=win_probability, expected_r=expected_r)

    def verdict(self, assessment: Assessment) -> str | None:
        if assessment.expected_r <= 0:
            return "negative_ev"
        if assessment.score < self.config.min_score:
            return "score"
        return None


@dataclass
class Sizing:
    quantity: float
    risk_dollars: float
    risk_fraction: float
    kelly: float
    capped: bool


class RiskAgent:
    """Sizes with the smaller of the user's risk cap and fractional Kelly.

    Notional is also capped so each of the `max_open_positions` slots gets an
    equal share of buying power. Tight intraday stops often want more notional
    than a cash account has, so small accounts will see many capped entries.
    """

    def __init__(self, config: DeskConfig) -> None:
        self.config = config

    def size(self, setup: Setup, assessment: Assessment, equity: float, committed_notional: float) -> Sizing | str:
        reward_risk = setup.reward_risk
        kelly = assessment.win_probability - (1 - assessment.win_probability) / reward_risk
        if kelly <= 0:
            return "kelly"

        risk_fraction = min(self.config.risk_per_trade_pct / 100, self.config.kelly_fraction * kelly)
        quantity = equity * risk_fraction / setup.risk_per_unit
        slot_notional = equity * self.config.max_leverage / self.config.max_open_positions
        remaining_notional = equity * self.config.max_leverage - committed_notional
        if remaining_notional < slot_notional * 0.5:
            return "buying_power"

        notional_cap = min(slot_notional, remaining_notional)
        capped = quantity * setup.entry > notional_cap
        if capped:
            quantity = notional_cap / setup.entry
        quantity = round(quantity, 4)
        if quantity <= 0 or quantity * setup.entry < 1:
            return "buying_power"

        return Sizing(
            quantity=quantity,
            risk_dollars=quantity * setup.risk_per_unit,
            risk_fraction=risk_fraction,
            kelly=kelly,
            capped=capped,
        )


@dataclass
class PaperOrder:
    trade_id: str
    setup: Setup
    sizing: Sizing
    assessment: Assessment
    placed_step: int


@dataclass
class PaperPosition:
    trade_id: str
    order: PaperOrder
    session: int
    open_step: int
    opened_at: str
    entry: float
    quantity: float
    stop: float
    target: float
    risk_per_unit: float
    entry_fee: float
    high_water_r: float = 0.0

    @property
    def side(self) -> DeskSide:
        return self.order.setup.side

    @property
    def direction(self) -> int:
        return 1 if self.side == "long" else -1

    def r_at(self, price: float) -> float:
        return self.direction * (price - self.entry) / self.risk_per_unit

    def gross_pnl_at(self, price: float) -> float:
        return self.direction * (price - self.entry) * self.quantity


@dataclass
class ExitFill:
    price: float
    reason: DeskExitReason


class ExecutorAgent:
    """Paper-only execution: next-bar-open fills, stop-first bar checks, slippage and fees."""

    def __init__(self, config: DeskConfig) -> None:
        self.config = config
        self.slippage = config.slippage_bps / 10_000
        self.fee_rate = config.fee_bps / 10_000

    def fill_price(self, order: PaperOrder, bar: Bar) -> float | str:
        setup = order.setup
        direction = 1 if setup.side == "long" else -1
        price = bar.open * (1 + direction * self.slippage)
        if direction * (price - setup.stop) <= 0:
            return "gap_stop"
        if direction * (price - setup.target) >= 0:
            return "gap_target"
        return price

    def fee(self, price: float, quantity: float) -> float:
        return price * quantity * self.fee_rate

    def check_exit(self, position: PaperPosition, bar: Bar, initial_stop: float) -> ExitFill | None:
        direction = position.direction
        stop_hit = bar.low <= position.stop if direction == 1 else bar.high >= position.stop
        if stop_hit:
            # A gap through the stop fills at the open, not the stop: stops are not guarantees.
            raw = min(position.stop, bar.open) if direction == 1 else max(position.stop, bar.open)
            reason: DeskExitReason = "trail" if position.stop != initial_stop else "stop"
            return ExitFill(price=raw * (1 - direction * self.slippage), reason=reason)

        target_hit = bar.high >= position.target if direction == 1 else bar.low <= position.target
        if target_hit:
            return ExitFill(price=position.target, reason="target")
        return None

    def bell_exit(self, position: PaperPosition, bar: Bar) -> ExitFill:
        return ExitFill(price=bar.close * (1 - position.direction * self.slippage), reason="bell")

    def trail(self, position: PaperPosition, bar: Bar) -> float | None:
        """Returns a tighter stop once the trade has run `trail_after_r`, else None."""
        favorable = bar.high if position.direction == 1 else bar.low
        position.high_water_r = max(position.high_water_r, position.r_at(favorable))
        if position.high_water_r < self.config.trail_after_r:
            return None

        locked_r = position.high_water_r - 1.0
        candidate = position.entry + position.direction * locked_r * position.risk_per_unit
        if position.direction * (candidate - position.stop) <= 0:
            return None
        return candidate


class LoggerAgent:
    """Records every decision with its reason and keeps the pipeline counters."""

    def __init__(self) -> None:
        self.events: list[DeskEvent] = []
        self.counts = DeskPipelineCounts()
        self.kills: dict[tuple[DeskAgent, str], int] = {}

    def log(
        self,
        *,
        step: int,
        session: int,
        clock: str,
        agent: DeskAgent,
        kind: str,
        message: str,
        symbol: str | None = None,
    ) -> None:
        self.events.append(
            DeskEvent(step=step, session=session, clock=clock, agent=agent, symbol=symbol, kind=kind, message=message)
        )
        self.counts.logger_reasons += 1

    def kill(self, agent: DeskAgent, code: str) -> None:
        self.kills[(agent, code)] = self.kills.get((agent, code), 0) + 1


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def map_journal_tags(tags: list[str]) -> DeskSetup | None:
    lowered = [tag.lower() for tag in tags]
    for setup, keywords in JOURNAL_TAG_KEYWORDS.items():
        if any(keyword in tag for tag in lowered for keyword in keywords):
            return setup
    return None
