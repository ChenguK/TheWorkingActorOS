"""breakdown details

Revision ID: 0024_breakdown_details
Revises: 0023_breakdown_classification
Create Date: 2026-06-26 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0024_breakdown_details"
down_revision: str | None = "0023_breakdown_classification"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "opportunities",
        sa.Column("source_metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    )
    op.add_column(
        "opportunities",
        sa.Column("production_details", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    )
    op.add_column(
        "opportunities",
        sa.Column("role_details", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    )
    op.add_column("opportunities", sa.Column("ai_summary", sa.Text(), nullable=True))
    op.alter_column("opportunities", "source_metadata", server_default=None)
    op.alter_column("opportunities", "production_details", server_default=None)
    op.alter_column("opportunities", "role_details", server_default=None)


def downgrade() -> None:
    op.drop_column("opportunities", "ai_summary")
    op.drop_column("opportunities", "role_details")
    op.drop_column("opportunities", "production_details")
    op.drop_column("opportunities", "source_metadata")
