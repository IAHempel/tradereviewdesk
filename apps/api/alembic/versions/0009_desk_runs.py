"""Create desk_runs table for paper agent desk sessions."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009_desk_runs"
down_revision = "0008_report_job_usage_metrics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "desk_runs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mode", sa.Text(), nullable=False, server_default="paper"),
        sa.Column("data_source", sa.Text(), nullable=False, server_default="synthetic"),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_desk_runs_user_id_created_at", "desk_runs", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_desk_runs_user_id_created_at", table_name="desk_runs")
    op.drop_table("desk_runs")
