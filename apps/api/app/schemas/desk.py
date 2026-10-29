import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

DeskSetup = Literal["breakout", "sweep_reclaim", "trend_pullback", "mean_reversion"]
DeskDataSource = Literal["synthetic", "polygon", "alpaca"]
DeskAgent = Literal["scout", "flow", "filter", "analyst", "risk", "executor", "logger"]
DeskSide = Literal["long", "short"]
DeskExitReason = Literal["stop", "trail", "target", "bell"]
DeskScanStatus = Literal["killed", "ordered"]

DESK_SETUPS: tuple[DeskSetup, ...] = ("breakout", "sweep_reclaim", "trend_pullback", "mean_reversion")
DESK_DISCLAIMER = (
    "Paper session on a synthetic market tape. Fills, prices, and P&L are simulated to show how your rules behave. "
    "Nothing here is a trade signal, a forecast, or evidence of real-world profitability."
)
HISTORICAL_DESK_DISCLAIMER = (
    "Paper replay of real historical 5-minute bars. Fills are simulated at bar opens with assumed slippage and fees, "
    "so real executions would differ. How your rules did on these days is not a forecast or a trade signal."
)
_SYMBOL_PATTERN = re.compile(r"^[A-Z0-9.\-]{1,12}$")


class DeskConfig(BaseModel):
    data_source: DeskDataSource = "synthetic"
    end_date: date | None = None
    symbols: list[str] = Field(default_factory=list, max_length=8)
    starting_balance: float = Field(default=500.0, ge=50, le=1_000_000)
    risk_per_trade_pct: float = Field(default=1.0, gt=0, le=3)
    kelly_fraction: float = Field(default=0.25, gt=0, le=1)
    max_open_positions: int = Field(default=3, ge=1, le=6)
    max_daily_loss_pct: float = Field(default=3.0, gt=0, le=10)
    max_consecutive_losses: int = Field(default=3, ge=1, le=10)
    min_reward_risk: float = Field(default=1.5, ge=1, le=5)
    min_score: int = Field(default=55, ge=0, le=100)
    trail_after_r: float = Field(default=1.5, ge=0.5, le=5)
    max_leverage: float = Field(default=1.0, ge=0.25, le=4)
    fee_bps: float = Field(default=1.0, ge=0, le=50)
    slippage_bps: float = Field(default=2.0, ge=0, le=50)
    sessions: int = Field(default=1, ge=1, le=5)
    allowed_setups: list[DeskSetup] = Field(default_factory=lambda: list(DESK_SETUPS), min_length=1)
    use_journal_priors: bool = True
    use_trade_flow: bool = True
    flow_veto: float = Field(default=0.35, ge=0.05, le=1.0)
    seed: int | None = Field(default=None, ge=0, le=2**31 - 1)

    @field_validator("symbols")
    @classmethod
    def normalize_symbols(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for raw in value:
            symbol = raw.strip().upper()
            if not symbol:
                continue
            if not _SYMBOL_PATTERN.match(symbol):
                raise ValueError(f"Unsupported symbol: {raw!r}")
            if symbol not in normalized:
                normalized.append(symbol)
        return normalized

    @field_validator("allowed_setups")
    @classmethod
    def dedupe_setups(cls, value: list[DeskSetup]) -> list[DeskSetup]:
        return [setup for setup in DESK_SETUPS if setup in value]


class DeskPipelineCounts(BaseModel):
    scout_flagged: int = 0
    filter_killed: int = 0
    analyst_scored: int = 0
    analyst_killed: int = 0
    risk_sized: int = 0
    risk_rejected: int = 0
    executor_fills: int = 0
    executor_cancels: int = 0
    executor_exits: int = 0
    stops_trailed: int = 0
    stops_widened: int = 0
    logger_reasons: int = 0
    flow_vetoes: int = 0


class DeskPosition(BaseModel):
    trade_id: str
    symbol: str
    side: DeskSide
    setup: DeskSetup
    entry: float
    stop: float
    target: float
    last: float
    r_now: float
    unrealized: float


class DeskScanMark(BaseModel):
    symbol: str
    setup: DeskSetup
    side: DeskSide
    status: DeskScanStatus


class DeskFrame(BaseModel):
    step: int
    session: int
    clock: str
    equity: float
    positions: list[DeskPosition] = Field(default_factory=list)
    scans: list[DeskScanMark] = Field(default_factory=list)
    pipeline: DeskPipelineCounts
    halted: bool = False
    flow: dict[str, float] = Field(default_factory=dict)


class DeskEvent(BaseModel):
    step: int
    session: int
    clock: str
    agent: DeskAgent
    symbol: str | None = None
    kind: str
    message: str


class DeskTrade(BaseModel):
    id: str
    symbol: str
    side: DeskSide
    setup: DeskSetup
    session: int
    open_step: int
    close_step: int
    opened_at: str
    closed_at: str
    entry: float
    exit: float
    stop_initial: float
    stop_final: float
    target: float
    quantity: float
    risk_dollars: float
    fees: float
    pnl: float
    r_multiple: float
    exit_reason: DeskExitReason
    score: int
    win_probability: float
    thesis: str


class DeskSetupEdge(BaseModel):
    setup: DeskSetup
    enabled: bool
    prior_wins: float
    prior_losses: float
    journal_wins: int
    journal_losses: int
    live_wins: int
    live_losses: int
    posterior_win_rate: float
    trades: int
    avg_r: float | None = None


class DeskKillReason(BaseModel):
    agent: DeskAgent
    code: str
    label: str
    count: int


class DeskDataSourceInfo(BaseModel):
    id: DeskDataSource
    label: str
    available: bool
    detail: str


class DeskMonteCarloBand(BaseModel):
    trade_index: int
    p5: float
    p25: float
    p50: float
    p75: float
    p95: float


class DeskMonteCarlo(BaseModel):
    paths: int
    trades_per_path: int
    sample_size: int
    bands: list[DeskMonteCarloBand]
    probability_below_start: float
    probability_drawdown_20: float
    median_multiple: float


class DeskSummary(BaseModel):
    starting_balance: float
    ending_balance: float
    net_pnl: float
    return_pct: float
    multiple: float
    trades: int
    wins: int
    losses: int
    win_rate: float | None = None
    avg_win_r: float | None = None
    avg_loss_r: float | None = None
    expectancy_r: float | None = None
    profit_factor: float | None = None
    max_drawdown_pct: float
    best_trade: float | None = None
    worst_trade: float | None = None
    fees_paid: float
    sessions: int
    halted_sessions: int


class DeskRunSummaryResponse(BaseModel):
    id: str
    created_at: str
    mode: Literal["paper"] = "paper"
    data_source: DeskDataSource = "synthetic"
    config: DeskConfig
    summary: DeskSummary


class DeskRunResponse(DeskRunSummaryResponse):
    session_labels: list[str] = Field(default_factory=list)
    pipeline: DeskPipelineCounts
    setup_edges: list[DeskSetupEdge]
    kill_reasons: list[DeskKillReason]
    trades: list[DeskTrade]
    frames: list[DeskFrame]
    events: list[DeskEvent]
    monte_carlo: DeskMonteCarlo | None = None
    flow_source: str = "bar proxy"
    disclaimer: str = DESK_DISCLAIMER
