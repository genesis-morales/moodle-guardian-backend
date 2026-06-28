"""add instructions jsonb to snapshots

Revision ID: 0028c9ad82a1
Revises: 9b1d7c4a2e30
Create Date: 2026-06-26 14:37:59.900543

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0028c9ad82a1'
down_revision: Union[str, Sequence[str], None] = '9b1d7c4a2e30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Columna para los PDFs de instrucciones (mismo patrón JSONB que events).
    op.add_column(
        "snapshots",
        sa.Column(
            "instructions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )
    # Tabla huérfana de un intento anterior (enfoque de tabla aparte que se
    # descartó a favor de la columna JSONB). IF EXISTS para no fallar en una
    # base de datos limpia que nunca la tuvo.
    op.execute("DROP TABLE IF EXISTS instruction_snapshots")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("snapshots", "instructions")
