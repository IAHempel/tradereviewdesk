from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.desk import DeskMonteCarlo

BinaryAsset = Literal["BTC", "ETH", "SOL", "XRP", "DOGE"]
BinaryDataSource = Literal["synthetic", "coinbase"]
BinarySide = Literal["up", "down"]
BINARY_ASSETS: tuple[BinaryAsset, ...] = ("BTC", "ETH", "SOL", "XRP", "DOGE")

BINARY_DISCLAIMER = (
    "Paper simulation. The underlying prices are real (or synthetic, if chosen), but the prediction market is modeled: "
    "the crowd's prices are this desk's fair value delayed and blurred by the assumptions below, and fills follow a "
    "trade-through rule with a queue probability. P&L depends heavily on those assumptions; compare it with the "
    "efficient-crowd baseline. Nothing here reflects a real venue, a trade signal, or available liquidity."
)


class BinaryConfig(BaseModel):
    assets: list[BinaryAsset] = Field(default_factory=lambda: ["BTC", "ETH", "SOL"], min_length=1, max_length=5)
    data_source: BinaryDataSource = "synthetic"
    end_at: datetime | None = None
    hours: int = Field(default=4, ge=1, le=12)
    starting_balance: float = Field(default=1000.0, ge=50, le=1_000_000)
    shares_per_level: int = Field(default=10, ge=1, le=500)
    levels: int = Field(default=3, ge=1, le=5)
    level_step_cents: float = Field(default=1.0, ge=0.5, le=5)
    half_spread_cents: float = Field(default=2.0, ge=0.5, le=10)
    max_shares_per_side: int = Field(default=100, ge=1, le=5000)
    inventory_skew_cents: float = Field(default=3.0, ge=0, le=20)
    stop_quoting_minutes: int = Field(default=2, ge=0, le=10)
    queue_fill_probability: float = Field(default=0.3, ge=0.05, le=1)
    maker_fee_bps: float = Field(default=0.0, ge=0, le=200)
    crowd_lag_minutes: int = Field(default=1, ge=0, le=5)
    crowd_noise_cents: float = Field(default=1.0, ge=0, le=10)
    dislocation_half_life_minutes: float = Field(default=3.0, ge=0.5, le=30)
    crowd_spread_cents: float = Field(default=2.0, ge=0.5, le=10)
    seed: int | None = Field(default=None, ge=0, le=2**31 - 1)

    @field_validator("assets")
    @classmethod
    def dedupe_assets(cls, value: list[BinaryAsset]) -> list[BinaryAsset]:
        return [asset for asset in BINARY_ASSETS if asset in value]


class BinaryMinute(BaseModel):
    """One minute of the run, across all assets."""

    t: str
    equity: float
    fills: int
    inventory: dict[str, float]


class BinaryAssetSeries(BaseModel):
    """Per-minute series for one asset, aligned with `minutes`."""

    asset: BinaryAsset
    price: list[float]
    fair_up: list[float]
    crowd_up: list[float]
    bid_up: list[float | None]
    bid_down: list[float | None]


class BinaryWindow(BaseModel):
    asset: BinaryAsset
    index: int
    start: str
    end: str
    start_minute: int
    open: float
    close: float
    outcome: BinarySide
    up_shares: float
    down_shares: float
    up_cost: float
    down_cost: float
    pairs: float
    avg_pair_cost: float | None = None
    unpaired_side: BinarySide | None = None
    unpaired_shares: float
    fees: float
    pnl: float
    fills: int


class BinaryFill(BaseModel):
    t: str
    minute: int
    asset: BinaryAsset
    window_index: int
    side: BinarySide
    price: float
    shares: float
    level: int
    fair_up: float
    crowd_up: float


class BinarySummary(BaseModel):
    starting_balance: float
    ending_balance: float
    net_pnl: float
    return_pct: float
    windows: int
    windows_won: int
    window_win_rate: float | None = None
    fills: int
    fills_per_hour: float
    pairs_locked: float
    paired_share_pct: float | None = None
    avg_pair_cost: float | None = None
    paired_pnl: float
    unpaired_pnl: float
    fees: float
    max_drawdown_pct: float


class BinaryBaseline(BaseModel):
    """The same rules against a crowd with no lag and no noise: what the grid makes without an informational edge."""

    net_pnl: float
    fills: int
    pairs_locked: float
    window_win_rate: float | None = None


class BinaryRunSummaryResponse(BaseModel):
    id: str
    created_at: str
    mode: Literal["paper"] = "paper"
    data_source: BinaryDataSource
    config: BinaryConfig
    summary: BinarySummary
    baseline: BinaryBaseline


class BinaryRunResponse(BinaryRunSummaryResponse):
    minutes: list[BinaryMinute]
    series: list[BinaryAssetSeries]
    windows: list[BinaryWindow]
    fills: list[BinaryFill]
    fill_arrival: list[int]
    dislocation_half_life_minutes: float | None = None
    monte_carlo: DeskMonteCarlo | None = None
    notes: list[str] = Field(default_factory=list)
    disclaimer: str = BINARY_DISCLAIMER
