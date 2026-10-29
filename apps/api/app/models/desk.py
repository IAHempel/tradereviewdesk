from sqlalchemy import ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DeskRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "desk_runs"
    __table_args__ = (Index("idx_desk_runs_user_id_created_at", "user_id", "created_at"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    mode: Mapped[str] = mapped_column(Text, nullable=False, default="paper")
    data_source: Mapped[str] = mapped_column(Text, nullable=False, default="synthetic")
    config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    summary: Mapped[dict] = mapped_column(JSONB, nullable=False)
    result: Mapped[dict] = mapped_column(JSONB, nullable=False)
