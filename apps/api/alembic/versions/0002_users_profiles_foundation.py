"""Create users and profiles tables for the first database-backed path."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_users_profiles"
down_revision = "0001_initial_placeholder"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('create extension if not exists "pgcrypto";')

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("auth_provider_id", sa.Text(), nullable=False, unique=True),
        sa.Column("email", sa.Text(), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "profiles",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("trading_style", sa.String(length=32), nullable=False),
        sa.Column("pain_points", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("broker_platform", sa.String(length=255), nullable=True),
        sa.Column("onboarding_completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("trading_style in ('day','swing','options','mixed')", name="ck_profiles_trading_style"),
    )


def downgrade() -> None:
    op.drop_table("profiles")
    op.drop_table("users")
