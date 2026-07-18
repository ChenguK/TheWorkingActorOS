"""link source research items to matched breakdowns

Revision ID: 0052_source_matched_breakdown
Revises: 0051_manual_override_timestamps
Create Date: 2026-07-06 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0052_source_matched_breakdown"
down_revision: Union[str, None] = "0051_manual_override_timestamps"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "source_research_items",
        sa.Column("discovered_from_breakdown_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("source_research_items", sa.Column("discovery_reason", sa.Text(), nullable=True))
    op.add_column(
        "source_research_items",
        sa.Column("source_role_match_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_foreign_key(
        "fk_source_research_items_discovered_from_breakdown_id",
        "source_research_items",
        "opportunities",
        ["discovered_from_breakdown_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_source_research_items_discovered_from_breakdown_id",
        "source_research_items",
        ["discovered_from_breakdown_id"],
    )
    op.alter_column("source_research_items", "source_role_match_count", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_source_research_items_discovered_from_breakdown_id", table_name="source_research_items")
    op.drop_constraint(
        "fk_source_research_items_discovered_from_breakdown_id",
        "source_research_items",
        type_="foreignkey",
    )
    op.drop_column("source_research_items", "source_role_match_count")
    op.drop_column("source_research_items", "discovery_reason")
    op.drop_column("source_research_items", "discovered_from_breakdown_id")
