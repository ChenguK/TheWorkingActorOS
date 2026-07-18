"""breakdown classification

Revision ID: 0023_breakdown_classification
Revises: 0022_watch_lists
Create Date: 2026-06-26 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0023_breakdown_classification"
down_revision: str | None = "0022_watch_lists"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "opportunities",
        sa.Column("breakdown_classification", sa.String(length=80), server_default="Unknown", nullable=False),
    )
    op.add_column("opportunities", sa.Column("rejection_reason", sa.Text(), nullable=True))
    op.create_check_constraint(
        "ck_opportunities_breakdown_classification",
        "opportunities",
        "breakdown_classification IN ('Acting Role', 'Background Role', 'Voiceover Role', "
        "'Theater Role', 'Commercial Role', 'Non-Acting Job', 'Crew Job', 'Unknown')",
    )
    op.alter_column("opportunities", "breakdown_classification", server_default=None)


def downgrade() -> None:
    op.drop_constraint("ck_opportunities_breakdown_classification", "opportunities", type_="check")
    op.drop_column("opportunities", "rejection_reason")
    op.drop_column("opportunities", "breakdown_classification")
