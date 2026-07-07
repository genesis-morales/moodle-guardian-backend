"""add connection_id to snapshots (snapshot por conexión)

Revision ID: b6c7d8e9f0a1
Revises: a5b6c7d8e9f0
Create Date: 2026-07-06 12:30:00.000000

El snapshot pasa a llavearse por conexión (campus), no solo por cuenta. Nullable por
las filas históricas; se backfillean a la conexión aprende de la cuenta (join por
account_id = snapshots.user_id). No destructiva.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b6c7d8e9f0a1"
down_revision: Union[str, Sequence[str], None] = "a5b6c7d8e9f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("snapshots", sa.Column("connection_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "fk_snapshots_connection_id",
        "snapshots",
        "moodle_connections",
        ["connection_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_snapshots_connection_id", "snapshots", ["connection_id"])

    # Backfill: cada snapshot histórico -> la conexión aprende de su cuenta.
    op.execute(
        """
        UPDATE snapshots s
        SET connection_id = mc.id
        FROM moodle_connections mc
        WHERE mc.account_id = s.user_id
          AND mc.site_key = 'aprende'
        """
    )


def downgrade() -> None:
    op.drop_index("ix_snapshots_connection_id", table_name="snapshots")
    op.drop_constraint("fk_snapshots_connection_id", "snapshots", type_="foreignkey")
    op.drop_column("snapshots", "connection_id")
