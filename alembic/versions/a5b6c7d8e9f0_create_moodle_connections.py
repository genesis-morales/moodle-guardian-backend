"""create moodle_connections + backfill (multi-campus)

Revision ID: a5b6c7d8e9f0
Revises: f4a5b6c7d8e9
Create Date: 2026-07-06 12:05:00.000000

Extrae la conexión Moodle de `users` a una entidad propia `moodle_connections` (1..N
por cuenta), para soportar multi-campus/multi-universidad. El token/moodle_user_id ya
no viven solo en `users`: la fuente de verdad pasa a ser la conexión, llaveada por
`(site_key, moodle_user_id)`.

Backfill: una fila por usuario con `site_key='aprende'`. NO es un default asumido: los
tokens existentes se emitieron contra la URL global (que apunta solo a aprende), así que
aprende es lo que factualmente son. No destructiva: `users.moodle_token`/`moodle_user_id`
se conservan una release por rollback/scan legacy.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a5b6c7d8e9f0"
down_revision: Union[str, Sequence[str], None] = "f4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "moodle_connections",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("site_key", sa.String(), nullable=False),
        sa.Column("moodle_user_id", sa.BigInteger(), nullable=False),
        sa.Column("moodle_token", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("token_failure_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_scan_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_key", "moodle_user_id", name="uq_connection_site_user"),
    )
    op.create_index("ix_moodle_connections_account_id", "moodle_connections", ["account_id"])
    op.create_index("ix_moodle_connections_site_key", "moodle_connections", ["site_key"])
    op.create_index("ix_moodle_connections_moodle_user_id", "moodle_connections", ["moodle_user_id"])
    op.create_index("ix_moodle_connections_is_active", "moodle_connections", ["is_active"])

    # Backfill: cada usuario existente -> 1 conexión 'aprende' con su token actual.
    op.execute(
        """
        INSERT INTO moodle_connections (
            account_id, site_key, moodle_user_id, moodle_token,
            is_active, token_failure_count, last_scan_at, created_at, updated_at
        )
        SELECT
            id, 'aprende', moodle_user_id, moodle_token,
            is_active, token_failure_count, last_scan_at, now(), now()
        FROM users
        """
    )


def downgrade() -> None:
    op.drop_index("ix_moodle_connections_is_active", table_name="moodle_connections")
    op.drop_index("ix_moodle_connections_moodle_user_id", table_name="moodle_connections")
    op.drop_index("ix_moodle_connections_site_key", table_name="moodle_connections")
    op.drop_index("ix_moodle_connections_account_id", table_name="moodle_connections")
    op.drop_table("moodle_connections")
