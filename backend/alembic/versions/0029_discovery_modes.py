"""discovery modes

Revision ID: 0029_discovery_modes
Revises: 0028_breakdown_roles
Create Date: 2026-07-01 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0029_discovery_modes"
down_revision: str | None = "0028_breakdown_roles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("discovery_runs", sa.Column("discovery_mode", sa.String(length=40), nullable=False, server_default="All"))
    op.add_column("discovery_runs", sa.Column("total_found", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("discovery_runs", sa.Column("total_saved", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("discovery_runs", sa.Column("total_rejected", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("discovery_runs", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("discovery_runs", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        "UPDATE discovery_runs SET total_found = opportunities_found, "
        "total_saved = opportunities_created, total_rejected = opportunities_hidden"
    )
    op.create_check_constraint(
        "ck_discovery_runs_discovery_mode",
        "discovery_runs",
        "discovery_mode IN ('Theater', 'FilmTV', 'All')",
    )
    op.alter_column("discovery_runs", "discovery_mode", server_default=None)
    op.alter_column("discovery_runs", "total_found", server_default=None)
    op.alter_column("discovery_runs", "total_saved", server_default=None)
    op.alter_column("discovery_runs", "total_rejected", server_default=None)


def downgrade() -> None:
    op.drop_constraint("ck_discovery_runs_discovery_mode", "discovery_runs", type_="check")
    op.drop_column("discovery_runs", "completed_at")
    op.drop_column("discovery_runs", "notes")
    op.drop_column("discovery_runs", "total_rejected")
    op.drop_column("discovery_runs", "total_saved")
    op.drop_column("discovery_runs", "total_found")
    op.drop_column("discovery_runs", "discovery_mode")
