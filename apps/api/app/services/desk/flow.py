"""Order flow: who is pressing, buyers or sellers, and how hard.

The Flow agent keeps a decaying memory of signed volume over the last 24 bars of
the session and turns it into a volume-weighted imbalance from -1 (all selling)
to +1 (all buying). Signed volume comes from real trade prints when the feed has
them (each print classified by the tick rule) and otherwise from a bar proxy:
volume times where the bar closed inside its range. The proxy is labelled as
such everywhere it is used.
"""

from dataclasses import dataclass, field

from app.services.desk.market import Bar

FLOW_LAGS = 24
FLOW_DECAY = 0.9
# Readings shrink toward neutral until this many bars of the session are in memory.
FLOW_MIN_BARS = 6
FLOW_LEVELS = (
    (-0.5, "strong sell"),
    (-0.2, "sell"),
    (0.0, "lean sell"),
    (0.2, "lean buy"),
    (0.5, "buy"),
)
TRADE_FLOW_SOURCE = "trade prints"
PROXY_FLOW_SOURCE = "bar proxy"


@dataclass(frozen=True)
class FlowSlot:
    buy_volume: float
    sell_volume: float

    @property
    def signed(self) -> float:
        return self.buy_volume - self.sell_volume

    @property
    def total(self) -> float:
        return self.buy_volume + self.sell_volume


def proxy_flow(bar: Bar) -> FlowSlot:
    """Splits bar volume by close location: a close at the high is all buying, at the low all selling."""
    spread = bar.high - bar.low
    location = 0.0 if spread <= 0 else ((bar.close - bar.low) - (bar.high - bar.close)) / spread
    buy_share = (1 + location) / 2
    return FlowSlot(bar.volume * buy_share, bar.volume * (1 - buy_share))


class TickRuleClassifier:
    """Classifies prints as buys on an uptick and sells on a downtick; flat prints keep the last side."""

    def __init__(self) -> None:
        self.last_price: float | None = None
        self.last_side = 0

    def side(self, price: float) -> int:
        if self.last_price is not None and price != self.last_price:
            self.last_side = 1 if price > self.last_price else -1
        self.last_price = price
        return self.last_side


def flow_level(imbalance: float) -> str:
    for upper, label in FLOW_LEVELS:
        if imbalance < upper:
            return label
    return "strong buy"


@dataclass
class FlowMemory:
    """Per-symbol rolling flow for the current session."""

    slots: list[FlowSlot] = field(default_factory=list)

    def reset(self) -> None:
        self.slots.clear()

    @property
    def warmed_up(self) -> bool:
        return len(self.slots) >= FLOW_MIN_BARS

    def push(self, slot: FlowSlot) -> float:
        """Adds the latest bar's flow and returns the imbalance, shrunk toward 0 while memory is short."""
        self.slots.append(slot)
        del self.slots[:-FLOW_LAGS]
        weighted_signed = 0.0
        weighted_total = 0.0
        for lag, item in enumerate(reversed(self.slots)):
            weight = FLOW_DECAY**lag
            weighted_signed += weight * item.signed
            weighted_total += weight * item.total
        if weighted_total <= 0:
            return 0.0
        return weighted_signed / weighted_total * min(1.0, len(self.slots) / FLOW_MIN_BARS)
