"""add email to users (identidad de cuenta)

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-07-06 12:00:00.000000

La identidad de una cuenta pasa a ser el `email` (independiente del canal de
notificación y llave de facturación), no el `telegram_chat_id` ni el `moodle_user_id`.
Nullable porque las filas legacy no tienen email (el usuario se los pone luego); el
registro nuevo lo exige. Índice único: una cuenta por email.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4a5b6c7d8e9"
down_revision: Union[str, Sequence[str], None] = "e3f4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email", sa.String(), nullable=True))
    # Índice único: sirve de unicidad y de lookup por email en el registro.
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # Relaja moodle_user_id: deja de ser único global (con multi-campus el mismo
    # userid puede repetirse entre campus/personas). Se conserva el índice para
    # lookups del scan legacy, pero SIN unicidad. La identidad de conexión vive en
    # moodle_connections(site_key, moodle_user_id).
    op.drop_index("ix_users_moodle_user_id", table_name="users")
    op.create_index("ix_users_moodle_user_id", "users", ["moodle_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_moodle_user_id", table_name="users")
    op.create_index("ix_users_moodle_user_id", "users", ["moodle_user_id"], unique=True)
    op.drop_index("ix_users_email", table_name="users")
    op.drop_column("users", "email")
