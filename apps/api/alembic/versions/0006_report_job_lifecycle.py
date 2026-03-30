"""Add lifecycle columns to report_jobs for job-based generation."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_report_job_flow"
down_revision = "0005_trade_user_fk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("report_jobs", sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("report_jobs", sa.Column("raw_model_output", sa.Text(), nullable=True))
    op.add_column("report_jobs", sa.Column("parsed_output", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("report_jobs", "parsed_output")
    op.drop_column("report_jobs", "raw_model_output")
    op.drop_column("report_jobs", "attempts")
