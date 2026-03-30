from sqlalchemy import Date, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class TradeEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "trade_entries"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    trade_date: Mapped[str] = mapped_column(Date, nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(32), nullable=False)
    side: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity: Mapped[float | None] = mapped_column(Numeric(18, 4))
    entry_price: Mapped[float | None] = mapped_column(Numeric(18, 6))
    exit_price: Mapped[float | None] = mapped_column(Numeric(18, 6))
    pnl: Mapped[float | None] = mapped_column(Numeric(18, 2))
    fees: Mapped[float | None] = mapped_column(Numeric(18, 2))
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(32), default="manual", nullable=False)
