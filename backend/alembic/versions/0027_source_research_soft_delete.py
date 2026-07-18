"""source research soft delete

Revision ID: 0027_source_research_soft_delete
Revises: 0026_source_research_urls
Create Date: 2026-07-01 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0027_source_research_soft_delete"
down_revision: str | None = "0026_source_research_urls"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_source_research_items_status",
        "source_research_items",
        type_="check",
    )
    op.add_column(
        "source_research_items",
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "source_research_items",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "source_research_items",
        sa.Column("rejection_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "source_research_items",
        sa.Column("rejected_by_user", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "source_research_items",
        sa.Column("previous_status", sa.String(length=40), nullable=True),
    )
    op.create_check_constraint(
        "ck_source_research_items_status",
        "source_research_items",
        "status IN ('Suggested', 'Researching', 'Approved', 'Rejected', 'Active', 'Paused', 'Deleted')",
    )
    op.alter_column("source_research_items", "deleted", server_default=None)
    op.alter_column("source_research_items", "rejected_by_user", server_default=None)


def downgrade() -> None:
    op.execute(
        "UPDATE source_research_items "
        "SET status = COALESCE(previous_status, 'Rejected') "
        "WHERE status = 'Deleted'"
    )
    op.drop_constraint(
        "ck_source_research_items_status",
        "source_research_items",
        type_="check",
    )
    op.drop_column("source_research_items", "previous_status")
    op.drop_column("source_research_items", "rejected_by_user")
    op.drop_column("source_research_items", "rejection_reason")
    op.drop_column("source_research_items", "deleted_at")
    op.drop_column("source_research_items", "deleted")
    op.create_check_constraint(
        "ck_source_research_items_status",
        "source_research_items",
        "status IN ('Suggested', 'Researching', 'Approved', 'Rejected', 'Active', 'Paused')",
    )
