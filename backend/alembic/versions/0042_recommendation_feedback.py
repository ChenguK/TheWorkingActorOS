"""recommendation feedback

Revision ID: 0042_recommend_feedback
Revises: 0041_archetype_scores
Create Date: 2026-07-03 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0042_recommend_feedback"
down_revision: Union[str, None] = "0041_archetype_scores"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def uuid_pk() -> sa.Column:
    return sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True)


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "recommendation_feedback",
        uuid_pk(),
        sa.Column("actor_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recommendation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("feedback_type", sa.String(80), nullable=False),
        sa.Column("fit_reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("notes", sa.Text(), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["actor_profile_id"], ["actor_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recommendation_id"], ["agent_recommendations.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_recommendation_feedback_actor_profile_id", "recommendation_feedback", ["actor_profile_id"])
    op.create_index("ix_recommendation_feedback_opportunity_id", "recommendation_feedback", ["opportunity_id"])
    op.create_index("ix_recommendation_feedback_recommendation_id", "recommendation_feedback", ["recommendation_id"])


def downgrade() -> None:
    op.drop_index("ix_recommendation_feedback_recommendation_id", table_name="recommendation_feedback")
    op.drop_index("ix_recommendation_feedback_opportunity_id", table_name="recommendation_feedback")
    op.drop_index("ix_recommendation_feedback_actor_profile_id", table_name="recommendation_feedback")
    op.drop_table("recommendation_feedback")
