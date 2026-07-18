"""source research executive

Revision ID: 0025_source_research_executive
Revises: 0024_breakdown_details
Create Date: 2026-06-26 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0025_source_research_executive"
down_revision: str | None = "0024_breakdown_details"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "source_research_items",
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("reliability_notes", sa.Text(), nullable=True),
        sa.Column("user_rating", sa.Integer(), nullable=True),
        sa.Column("last_checked_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("suggested_by_ai", sa.Boolean(), nullable=False),
        sa.Column("provider_key", sa.String(length=160), nullable=True),
        sa.Column("added_to_discovery_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "category IN ('Public casting site', 'Casting office', 'Film commission', "
            "'Social media account', 'Production company', 'Theater company', 'Talent platform', 'Other')",
            name="ck_source_research_items_category",
        ),
        sa.CheckConstraint(
            "status IN ('Suggested', 'Researching', 'Approved', 'Rejected', 'Active', 'Paused')",
            name="ck_source_research_items_status",
        ),
        sa.CheckConstraint(
            "user_rating IS NULL OR (user_rating >= 1 AND user_rating <= 5)",
            name="ck_source_research_items_user_rating",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_source_research_items_provider_key"), "source_research_items", ["provider_key"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_source_research_items_provider_key"), table_name="source_research_items")
    op.drop_table("source_research_items")
