"""Align trade_entries.user_id with users.id for database-primary persistence."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_trade_user_fk"
down_revision = "0004_checklists_reports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("idx_trade_entries_user_id_date", table_name="trade_entries")
    op.alter_column(
        "trade_entries",
        "user_id",
        existing_type=sa.String(),
        type_=postgresql.UUID(as_uuid=False),
        postgresql_using="user_id::uuid",
        existing_nullable=False,
    )
    op.create_foreign_key(
        "fk_trade_entries_user_id_users",
        "trade_entries",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("idx_trade_entries_user_id_date", "trade_entries", ["user_id", "trade_date"])


def downgrade() -> None:
    op.drop_index("idx_trade_entries_user_id_date", table_name="trade_entries")
    op.drop_constraint("fk_trade_entries_user_id_users", "trade_entries", type_="foreignkey")
    op.alter_column(
        "trade_entries",
        "user_id",
        existing_type=postgresql.UUID(as_uuid=False),
        type_=sa.String(),
        postgresql_using="user_id::text",
        existing_nullable=False,
    )
    op.create_index("idx_trade_entries_user_id_date", "trade_entries", ["user_id", "trade_date"])
