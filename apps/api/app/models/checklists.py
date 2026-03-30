from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ChecklistTemplate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "checklist_templates"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    items: Mapped[list["ChecklistTemplateItem"]] = relationship(back_populates="template", cascade="all, delete-orphan")


class ChecklistTemplateItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "checklist_template_items"

    template_id: Mapped[str] = mapped_column(ForeignKey("checklist_templates.id", ondelete="CASCADE"), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    template: Mapped["ChecklistTemplate"] = relationship(back_populates="items")


class ChecklistRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "checklist_runs"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    template_id: Mapped[str | None] = mapped_column(ForeignKey("checklist_templates.id", ondelete="SET NULL"))
    session_date: Mapped[str] = mapped_column(Date, nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(32))
    setup_tag: Mapped[str | None] = mapped_column(String(100))
    reason_for_entry: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[int | None] = mapped_column(Integer)
    items: Mapped[list["ChecklistRunItem"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class ChecklistRunItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "checklist_run_items"

    checklist_run_id: Mapped[str] = mapped_column(ForeignKey("checklist_runs.id", ondelete="CASCADE"), nullable=False)
    template_item_id: Mapped[str | None] = mapped_column(ForeignKey("checklist_template_items.id", ondelete="SET NULL"))
    label_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    run: Mapped["ChecklistRun"] = relationship(back_populates="items")
