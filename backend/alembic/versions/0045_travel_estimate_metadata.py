"""add travel estimate metadata fields

Revision ID: 0045_travel_estimate_metadata
Revises: 0044_travel_estimates
Create Date: 2026-07-04 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0045_travel_estimate_metadata"
down_revision = "0044_travel_estimates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "travel_estimates",
        sa.Column("is_manual_override", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("travel_estimates", sa.Column("error_message", sa.Text(), nullable=True))
    op.alter_column("travel_estimates", "is_manual_override", server_default=None)


def downgrade() -> None:
    op.drop_column("travel_estimates", "error_message")
    op.drop_column("travel_estimates", "is_manual_override")
