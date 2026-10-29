"""NYSE regular-session hours, including the scheduled 1:00 pm early closes.

Full holidays need no rules here: a closed day simply has no regular-session
bars in the provider's data, so it never becomes a session.
"""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.services.desk.market import BAR_MINUTES, SESSION_OPEN_MINUTES

MARKET_TIMEZONE = ZoneInfo("America/New_York")
REGULAR_CLOSE_MINUTES = 16 * 60
EARLY_CLOSE_MINUTES = 13 * 60


def _thanksgiving(year: int) -> date:
    november_first = date(year, 11, 1)
    first_thursday = november_first + timedelta(days=(3 - november_first.weekday()) % 7)
    return first_thursday + timedelta(weeks=3)


def is_early_close(day: date) -> bool:
    """Day after Thanksgiving, plus July 3 and December 24 when they fall Monday to Thursday."""
    if day == _thanksgiving(day.year) + timedelta(days=1):
        return True
    if (day.month, day.day) in ((7, 3), (12, 24)) and day.weekday() < 4:
        return True
    return False


def session_bar_count(day: date) -> int:
    close = EARLY_CLOSE_MINUTES if is_early_close(day) else REGULAR_CLOSE_MINUTES
    return (close - SESSION_OPEN_MINUTES) // BAR_MINUTES


def market_today() -> date:
    return datetime.now(MARKET_TIMEZONE).date()
