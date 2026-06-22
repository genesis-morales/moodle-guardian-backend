"""add sent_reminders

Revision ID: 9b1d7c4a2e30
Revises: 4ddc72bcd967
Create Date: 2026-06-20 10:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "9b1d7c4a2e30"
down_revision: Union[str, Sequence[str], None] = "4ddc72bcd967"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sent_reminders",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("deliverable_key", sa.String(), nullable=True),
        sa.Column("notification_type", sa.String(), nullable=False),
        sa.Column("deadline_snapshot", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_sent_reminders_user_id", "sent_reminders", ["user_id"], unique=False
    )
    op.create_index(
        "ix_sent_reminders_deliverable_key",
        "sent_reminders",
        ["deliverable_key"],
        unique=False,
    )
    op.create_index(
        "ix_sent_reminders_sent_at", "sent_reminders", ["sent_at"], unique=False
    )
    # Índice de consulta para el dedup: "qué se le envió a este usuario de este tipo".
    op.create_index(
        "ix_sent_reminders_user_type",
        "sent_reminders",
        ["user_id", "notification_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_sent_reminders_user_type", table_name="sent_reminders")
    op.drop_index("ix_sent_reminders_sent_at", table_name="sent_reminders")
    op.drop_index("ix_sent_reminders_deliverable_key", table_name="sent_reminders")
    op.drop_index("ix_sent_reminders_user_id", table_name="sent_reminders")
    op.drop_table("sent_reminders")
