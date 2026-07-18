"""watch lists

Revision ID: 0022_watch_lists
Revises: 0021_discovery_settings
Create Date: 2026-06-26 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0022_watch_lists"
down_revision: str | None = "0021_discovery_settings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "watch_lists",
        sa.Column("actor_profile_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=False),
        sa.Column("terms", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("priority", sa.String(length=40), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("match_count", sa.Integer(), nullable=False),
        sa.Column("last_matched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_profile_id"], ["actor_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_watch_lists_actor_profile_id"), "watch_lists", ["actor_profile_id"], unique=False)
    op.add_column(
        "opportunities",
        sa.Column("watchlist_match_names", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    )
    op.add_column(
        "opportunities",
        sa.Column("watchlist_match_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("opportunities", sa.Column("watchlist_notification", sa.Text(), nullable=True))
    op.alter_column("opportunities", "watchlist_match_names", server_default=None)
    op.alter_column("opportunities", "watchlist_match_count", server_default=None)


def downgrade() -> None:
    op.drop_column("opportunities", "watchlist_notification")
    op.drop_column("opportunities", "watchlist_match_count")
    op.drop_column("opportunities", "watchlist_match_names")
    op.drop_index(op.f("ix_watch_lists_actor_profile_id"), table_name="watch_lists")
    op.drop_table("watch_lists")
