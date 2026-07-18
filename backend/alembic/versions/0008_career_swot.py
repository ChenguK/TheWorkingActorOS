"""career swot analysis

Revision ID: 0008_swot
Revises: 0007_intel
Create Date: 2026-06-23 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0008_swot"
down_revision: Union[str, None] = "0007_intel"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "career_swot_analyses",
        sa.Column("actor_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strengths", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("weaknesses", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("opportunities", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("threats", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_profile_id"], ["actor_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_career_swot_actor_profile_id", "career_swot_analyses", ["actor_profile_id"])


def downgrade() -> None:
    op.drop_index("ix_career_swot_actor_profile_id", table_name="career_swot_analyses")
    op.drop_table("career_swot_analyses")
