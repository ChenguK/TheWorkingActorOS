"""advanced career intelligence

Revision ID: 0011_advanced
Revises: 0010_history
Create Date: 2026-06-23 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_advanced"
down_revision: str | None = "0010_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dream_role_targets",
        sa.Column("actor_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_type", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("target_archetypes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("target_genres", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("target_offices", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "target_type IN ('Role', 'Show', 'Genre', 'Casting Office', 'Studio', 'Archetype')",
            name="ck_dream_role_targets_type",
        ),
        sa.ForeignKeyConstraint(["actor_profile_id"], ["actor_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dream_role_targets_actor_profile_id", "dream_role_targets", ["actor_profile_id"])
    op.create_index("ix_dream_role_targets_target_type", "dream_role_targets", ["target_type"])

    op.create_table(
        "quarterly_career_reviews",
        sa.Column("actor_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("quarter", sa.Integer(), nullable=False),
        sa.Column("report", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("quarter >= 1 AND quarter <= 4", name="ck_quarterly_career_reviews_quarter"),
        sa.ForeignKeyConstraint(["actor_profile_id"], ["actor_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quarterly_career_reviews_actor_profile_id", "quarterly_career_reviews", ["actor_profile_id"])
    op.create_index("ix_quarterly_career_reviews_period", "quarterly_career_reviews", ["year", "quarter"])


def downgrade() -> None:
    op.drop_index("ix_quarterly_career_reviews_period", table_name="quarterly_career_reviews")
    op.drop_index("ix_quarterly_career_reviews_actor_profile_id", table_name="quarterly_career_reviews")
    op.drop_table("quarterly_career_reviews")
    op.drop_index("ix_dream_role_targets_target_type", table_name="dream_role_targets")
    op.drop_index("ix_dream_role_targets_actor_profile_id", table_name="dream_role_targets")
    op.drop_table("dream_role_targets")
