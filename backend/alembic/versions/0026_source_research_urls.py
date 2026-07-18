"""source research urls

Revision ID: 0026_source_research_urls
Revises: 0025_source_research_executive
Create Date: 2026-07-01 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0026_source_research_urls"
down_revision: str | None = "0025_source_research_executive"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("source_research_items", sa.Column("base_url", sa.String(length=1000), nullable=True))
    op.add_column("source_research_items", sa.Column("suggested_specific_url", sa.String(length=1000), nullable=True))
    op.add_column("source_research_items", sa.Column("approved_discovery_url", sa.String(length=1000), nullable=True))
    op.add_column("source_research_items", sa.Column("last_researched_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "source_research_items",
        sa.Column("approved_by_user", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.execute("UPDATE source_research_items SET base_url = source_url WHERE base_url IS NULL")
    op.alter_column("source_research_items", "approved_by_user", server_default=None)


def downgrade() -> None:
    op.drop_column("source_research_items", "approved_by_user")
    op.drop_column("source_research_items", "last_researched_date")
    op.drop_column("source_research_items", "approved_discovery_url")
    op.drop_column("source_research_items", "suggested_specific_url")
    op.drop_column("source_research_items", "base_url")
