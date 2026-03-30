"""Add usage metrics tracking to report jobs."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008_report_job_usage_metrics"
down_revision = "0007_billing_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("report_jobs", sa.Column("usage_metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("report_jobs", "usage_metrics")
