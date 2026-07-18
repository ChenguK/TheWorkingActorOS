"""add source health classification fields

Revision ID: 0046_source_health
Revises: 0045_travel_estimate_metadata
Create Date: 2026-07-04 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0046_source_health"
down_revision = "0045_travel_estimate_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("source_research_items", sa.Column("source_health", sa.String(length=80), nullable=False, server_default="Unchecked"))
    op.add_column("source_research_items", sa.Column("suggested_classification", sa.String(length=80), nullable=False, server_default="Needs Review"))
    op.add_column("source_research_items", sa.Column("health_reason", sa.Text(), nullable=True))
    op.add_column("source_research_items", sa.Column("http_status", sa.Integer(), nullable=True))
    op.add_column("source_research_items", sa.Column("page_title", sa.String(length=300), nullable=True))
    op.add_column("source_research_items", sa.Column("redirect_target", sa.String(length=1000), nullable=True))
    op.add_column("source_research_items", sa.Column("visible_text_excerpt", sa.Text(), nullable=True))
    op.create_check_constraint(
        "ck_source_research_items_source_health",
        "source_research_items",
        "source_health IN ('Unchecked', 'Active', 'Dead / Unavailable Domain', 'Placeholder Website', 'No Meaningful Content', 'Blocked', 'Needs Review')",
    )
    op.create_check_constraint(
        "ck_source_research_items_suggested_classification",
        "source_research_items",
        "suggested_classification IN ('Valid Breakdown Source', 'Casting Office', 'Production Company', 'Regional Resource', 'Watch List Source', 'Rejected', 'Not Useful', 'Relationship Source', 'Needs Review')",
    )
    op.alter_column("source_research_items", "source_health", server_default=None)
    op.alter_column("source_research_items", "suggested_classification", server_default=None)


def downgrade() -> None:
    op.drop_constraint("ck_source_research_items_suggested_classification", "source_research_items", type_="check")
    op.drop_constraint("ck_source_research_items_source_health", "source_research_items", type_="check")
    op.drop_column("source_research_items", "visible_text_excerpt")
    op.drop_column("source_research_items", "redirect_target")
    op.drop_column("source_research_items", "page_title")
    op.drop_column("source_research_items", "http_status")
    op.drop_column("source_research_items", "health_reason")
    op.drop_column("source_research_items", "suggested_classification")
    op.drop_column("source_research_items", "source_health")
