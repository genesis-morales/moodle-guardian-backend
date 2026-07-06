"""add items jsonb to snapshots (fuente rastreable genérica)

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-07-05 19:00:00.000000

Consolida las columnas por-tipo (assignments/events/instructions) en un único
`items` JSONB = {source_type: [item, ...]}, para que agregar una fuente nueva no
requiera cambios de esquema. No destructiva: las columnas viejas se conservan (se
dropean en una migración de limpieza posterior) y se backfillea `items` desde ellas.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, Sequence[str], None] = "d2e3f4a5b6c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "snapshots",
        sa.Column(
            "items",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )
    # Backfill: arma el dict genérico desde las columnas legacy de cada fila.
    op.execute(
        """
        UPDATE snapshots
        SET items = jsonb_build_object(
            'assignment', COALESCE(assignments, '[]'::jsonb),
            'event', COALESCE(events, '[]'::jsonb),
            'instruction', COALESCE(instructions, '[]'::jsonb)
        )
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("snapshots", "items")
