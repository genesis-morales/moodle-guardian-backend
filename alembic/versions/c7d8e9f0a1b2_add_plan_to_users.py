"""add plan (tier de suscripcion) to users

Revision ID: c7d8e9f0a1b2
Revises: b6c7d8e9f0a1
Create Date: 2026-07-06 13:00:00.000000

Siembra el tier de suscripcion elegido en el registro: "alerta" | "escudo" |
"guardian". El backend todavia NO gatea features por plan (eso es feat 3 + pago);
por ahora solo se guarda el tier. server_default 'alerta' puebla las filas legacy con
el free tier sin backfill manual.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7d8e9f0a1b2"
down_revision: Union[str, Sequence[str], None] = "b6c7d8e9f0a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("plan", sa.String(), nullable=False, server_default="alerta"),
    )


def downgrade() -> None:
    op.drop_column("users", "plan")
