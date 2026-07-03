"""add token_failure_count to users

Revision ID: d2e3f4a5b6c7
Revises: c1f2a3b4d5e6
Create Date: 2026-07-03 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d2e3f4a5b6c7"
down_revision: Union[str, Sequence[str], None] = "c1f2a3b4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Cuenta corridas consecutivas del scan que fallaron con MoodleTokenError.
    # Permite exigir un umbral antes de desactivar, para que un bache transitorio
    # de Moodle no baje a un usuario. Los usuarios existentes arrancan en 0.
    op.add_column(
        "users",
        sa.Column(
            "token_failure_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "token_failure_count")
