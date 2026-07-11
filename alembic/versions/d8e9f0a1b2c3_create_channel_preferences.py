"""create channel_preferences + backfill telegram (multicanal, feat 3)

Revision ID: d8e9f0a1b2c3
Revises: c7d8e9f0a1b2
Create Date: 2026-07-07 14:30:00.000000

Modela la preferencia de canal por cuenta (1..N): qué canales ACTIVÓ de verdad la
cuenta (subconjunto ⊆ techo del plan) y con qué dirección de entrega (chat_id para
telegram, correo para email). Es la fuente de verdad de "por dónde notificar" que el
catálogo de planes anticipaba para feat 3.

Backfill: una fila `channel='telegram'` por cada usuario con `telegram_chat_id` no nulo
(su dirección = ese chat_id). NO destructivo: `users.telegram_chat_id` se conserva como
columna legacy una release por rollback/preview mientras el envío pasa a leer esta tabla.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d8e9f0a1b2c3"
down_revision: Union[str, Sequence[str], None] = "c7d8e9f0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "channel_preferences",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("address", sa.String(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "channel", name="uq_channel_pref_account_channel"),
    )
    op.create_index(
        "ix_channel_preferences_account_id", "channel_preferences", ["account_id"]
    )

    # Backfill: cada usuario con Telegram vinculado -> 1 preferencia 'telegram' activa.
    op.execute(
        """
        INSERT INTO channel_preferences (
            account_id, channel, address, is_enabled, created_at, updated_at
        )
        SELECT id, 'telegram', telegram_chat_id, true, now(), now()
        FROM users
        WHERE telegram_chat_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index(
        "ix_channel_preferences_account_id", table_name="channel_preferences"
    )
    op.drop_table("channel_preferences")
