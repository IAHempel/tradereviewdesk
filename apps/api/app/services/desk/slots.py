"""Regular-session 5-minute slots shared by every historical bar provider."""

from dataclasses import dataclass
from datetime import date, datetime

from app.services.desk.calendar import MARKET_TIMEZONE, session_bar_count
from app.services.desk.market import BAR_MINUTES, SESSION_OPEN_MINUTES


@dataclass(frozen=True)
class SlotBar:
    """One regular-session bar: `slot` 0 is the 09:30 bar."""

    day: date
    slot: int
    open: float
    high: float
    low: float
    close: float
    volume: float


def slot_for(stamp: datetime) -> tuple[date, int] | None:
    """The trading day and slot a bar or print starting at `stamp` belongs to, or None outside regular hours."""
    local = stamp.astimezone(MARKET_TIMEZONE)
    slot, _ = divmod(local.hour * 60 + local.minute - SESSION_OPEN_MINUTES, BAR_MINUTES)
    if local.hour * 60 + local.minute < SESSION_OPEN_MINUTES or slot >= session_bar_count(local.date()):
        return None
    return local.date(), slot


def to_slot_bar(stamp: datetime, open_: float, high: float, low: float, close: float, volume: float) -> SlotBar | None:
    """A provider bar starting at `stamp`, or None if it is not an aligned regular-session bar."""
    located = slot_for(stamp)
    if located is None or stamp.astimezone(MARKET_TIMEZONE).minute % BAR_MINUTES:
        return None
    day, slot = located
    return SlotBar(day, slot, float(open_), float(high), float(low), float(close), float(volume or 0))
