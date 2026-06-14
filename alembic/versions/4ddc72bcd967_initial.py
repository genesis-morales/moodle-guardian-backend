"""initial

Revision ID: 4ddc72bcd967
Revises:
Create Date: 2026-06-13 18:45:05.652827
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "4ddc72bcd967"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("moodle_user_id", sa.BigInteger(), nullable=False),
        sa.Column("moodle_token", sa.String(), nullable=False),
        sa.Column("telegram_chat_id", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_scan_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_users_moodle_user_id", "users", ["moodle_user_id"], unique=True
    )
    op.create_index(
        "uq_users_telegram_chat_id_not_null",
        "users",
        ["telegram_chat_id"],
        unique=True,
        postgresql_where=sa.text("telegram_chat_id IS NOT NULL"),
    )

    op.create_table(
        "snapshots",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("moodle_user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "captured_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("assignments", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("events", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_snapshots_user_id", "snapshots", ["user_id"], unique=False)
    op.create_index(
        "ix_snapshots_moodle_user_id", "snapshots", ["moodle_user_id"], unique=False
    )
    op.create_index(
        "ix_snapshots_captured_at", "snapshots", ["captured_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_snapshots_captured_at", table_name="snapshots")
    op.drop_index("ix_snapshots_moodle_user_id", table_name="snapshots")
    op.drop_index("ix_snapshots_user_id", table_name="snapshots")
    op.drop_table("snapshots")

    op.drop_index("uq_users_telegram_chat_id_not_null", table_name="users")
    op.drop_index("ix_users_moodle_user_id", table_name="users")
    op.drop_table("users")