"""Create desk_live_sessions table for live paper desk sessions."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0010_desk_live_sessions"
down_revision = "0009_desk_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "desk_live_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("record", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_desk_live_sessions_user_id_created_at", "desk_live_sessions", ["user_id", "created_at"])
    op.create_index("idx_desk_live_sessions_status", "desk_live_sessions", ["status"])


def downgrade() -> None:
    op.drop_index("idx_desk_live_sessions_status", table_name="desk_live_sessions")
    op.drop_index("idx_desk_live_sessions_user_id_created_at", table_name="desk_live_sessions")
    op.drop_table("desk_live_sessions")
