from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    auth_provider_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)


class Profile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "profiles"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255))
    trading_style: Mapped[str] = mapped_column(String(32), nullable=False)
    pain_points: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, nullable=False)
    broker_platform: Mapped[str | None] = mapped_column(String(255))
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Watchlist(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "watchlists"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="Default Watchlist")
    is_default: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    symbols: Mapped[list["WatchlistSymbol"]] = relationship(back_populates="watchlist", cascade="all, delete-orphan")


class WatchlistSymbol(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "watchlist_symbols"

    watchlist_id: Mapped[str] = mapped_column(ForeignKey("watchlists.id", ondelete="CASCADE"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    display_order: Mapped[int] = mapped_column(default=0, nullable=False)
    watchlist: Mapped["Watchlist"] = relationship(back_populates="symbols")
