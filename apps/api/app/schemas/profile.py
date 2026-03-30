from typing import Literal

from pydantic import BaseModel, EmailStr


TradingStyle = Literal["day", "swing", "options", "mixed"]


class ProfileResponse(BaseModel):
    email: EmailStr
    display_name: str | None = None
    trading_style: TradingStyle
    pain_points: list[str] = []
    broker_platform: str | None = None
    onboarding_completed: bool = False


class ProfileUpdate(BaseModel):
    display_name: str | None = None
    trading_style: TradingStyle | None = None
    pain_points: list[str] | None = None
    broker_platform: str | None = None
    onboarding_completed: bool | None = None
