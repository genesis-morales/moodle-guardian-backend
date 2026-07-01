"""add scan_runs table

Revision ID: c1f2a3b4d5e6
Revises: 0028c9ad82a1
Create Date: 2026-06-30 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "c1f2a3b4d5e6"
down_revision: Union[str, Sequence[str], None] = "0028c9ad82a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Historial de corridas de jobs (observabilidad): convierte los logs
    # efímeros del runner en historial consultable.
    op.create_table(
        "scan_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("job_name", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_users", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "failures",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scan_runs_job_name", "scan_runs", ["job_name"])
    op.create_index("ix_scan_runs_finished_at", "scan_runs", ["finished_at"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_scan_runs_finished_at", table_name="scan_runs")
    op.drop_index("ix_scan_runs_job_name", table_name="scan_runs")
    op.drop_table("scan_runs")
