from sqlalchemy import Date, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ReportJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "report_jobs"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    report_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    input_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    raw_model_output: Mapped[str | None] = mapped_column(Text)
    parsed_output: Mapped[dict | None] = mapped_column(JSONB)
    usage_metrics: Mapped[dict | None] = mapped_column(JSONB)


class Report(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reports"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    report_job_id: Mapped[str | None] = mapped_column(ForeignKey("report_jobs.id", ondelete="SET NULL"))
    report_type: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    report_date: Mapped[str] = mapped_column(Date, nullable=False)
    input_summary: Mapped[dict] = mapped_column(JSONB, nullable=False)
    raw_model_output: Mapped[str | None] = mapped_column(Text)
    parsed_output: Mapped[dict] = mapped_column(JSONB, nullable=False)
