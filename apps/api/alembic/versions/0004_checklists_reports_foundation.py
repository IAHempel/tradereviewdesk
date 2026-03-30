"""Create checklist and report tables for the remaining core workflow artifacts."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_checklists_reports"
down_revision = "0003_watchlists_trades"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "checklist_templates",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_checklist_templates_user_id", "checklist_templates", ["user_id"])

    op.create_table(
        "checklist_template_items",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("template_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("checklist_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "checklist_runs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("checklist_templates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=True),
        sa.Column("setup_tag", sa.String(length=100), nullable=True),
        sa.Column("reason_for_entry", sa.Text(), nullable=False),
        sa.Column("confidence_score", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_checklist_runs_user_id_date", "checklist_runs", ["user_id", "session_date"])

    op.create_table(
        "checklist_run_items",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("checklist_run_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("checklist_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("template_item_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("checklist_template_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("label_snapshot", sa.String(length=255), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    op.create_table(
        "report_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("report_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("input_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_report_jobs_user_id_type", "report_jobs", ["user_id", "report_type", "created_at"])

    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("report_job_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("report_jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("report_type", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("input_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("raw_model_output", sa.Text(), nullable=True),
        sa.Column("parsed_output", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_reports_user_id_type_date", "reports", ["user_id", "report_type", "report_date"])


def downgrade() -> None:
    op.drop_index("idx_reports_user_id_type_date", table_name="reports")
    op.drop_table("reports")
    op.drop_index("idx_report_jobs_user_id_type", table_name="report_jobs")
    op.drop_table("report_jobs")
    op.drop_table("checklist_run_items")
    op.drop_index("idx_checklist_runs_user_id_date", table_name="checklist_runs")
    op.drop_table("checklist_runs")
    op.drop_table("checklist_template_items")
    op.drop_index("idx_checklist_templates_user_id", table_name="checklist_templates")
    op.drop_table("checklist_templates")
