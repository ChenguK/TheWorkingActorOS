"""agent system

Revision ID: 0002_agent_system
Revises: 0001_phase_1_schema
Create Date: 2026-06-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_agent_system"
down_revision: str | None = "0001_phase_1_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("assets", sa.Column("ai_suggested_tags", postgresql.JSONB(), nullable=False, server_default="[]"))
    op.add_column("assets", sa.Column("ai_suggested_archetypes", postgresql.JSONB(), nullable=False, server_default="[]"))
    op.add_column("assets", sa.Column("analysis_status", sa.String(60), nullable=False, server_default="pending"))
    op.add_column("assets", sa.Column("analysis_explanation", sa.Text(), nullable=True))

    op.add_column("opportunities", sa.Column("normalized_key", sa.String(500), nullable=True))
    op.add_column("opportunities", sa.Column("category", sa.String(120), nullable=True))
    op.add_column("opportunities", sa.Column("source_reliability_score", sa.Float(), nullable=False, server_default="0.7"))
    op.add_column("opportunities", sa.Column("is_duplicate", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("opportunities", sa.Column("audition_type", sa.String(40), nullable=False, server_default="Self-Tape"))
    op.add_column("opportunities", sa.Column("audition_travel_hours", sa.Float(), nullable=True))
    op.create_index("ix_opportunities_normalized_key", "opportunities", ["normalized_key"])

    op.create_table(
        "agent_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_version", sa.String(60), nullable=False, server_default="strategy-v1"),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("match_type", sa.String(80), nullable=False),
        sa.Column("display_opportunity", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("score_breakdown", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("audition_type", sa.String(40), nullable=False),
        sa.Column("audition_travel_hours", sa.Float(), nullable=True),
        sa.Column("audition_decision", sa.String(80), nullable=False),
        sa.Column("audition_explanation", sa.Text(), nullable=False),
        sa.Column("travel_explanation", sa.Text(), nullable=False),
        sa.Column("archetype_explanation", sa.Text(), nullable=False),
        sa.Column("asset_explanation", sa.Text(), nullable=False),
        sa.Column("submission_strategy_explanation", sa.Text(), nullable=False),
        sa.Column("recommended_headshot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("recommended_reel_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("recommended_resume_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("recommended_slate_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("recommended_note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_profile_id"], ["actor_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recommended_headshot_id"], ["assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["recommended_reel_id"], ["assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["recommended_resume_id"], ["assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["recommended_slate_id"], ["assets.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_agent_recommendations_opportunity_id", "agent_recommendations", ["opportunity_id"])
    op.create_index("ix_agent_recommendations_actor_profile_id", "agent_recommendations", ["actor_profile_id"])
    op.create_index("ix_agent_recommendations_score", "agent_recommendations", ["score"])
    op.create_index("ix_agent_recommendations_match_type", "agent_recommendations", ["match_type"])

    op.create_table(
        "learning_insights",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("actor_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trends", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("recommendation_weights", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_profile_id"], ["actor_profiles.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_learning_insights_actor_profile_id", "learning_insights", ["actor_profile_id"])

    op.create_table(
        "career_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("actor_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strengths", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("growth_opportunities", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("archetypes_to_expand", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("recommended_headshots", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("recommended_role_types", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("strong_match_roles", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("growth_match_roles", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("stretch_roles", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_profile_id"], ["actor_profiles.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_career_recommendations_actor_profile_id", "career_recommendations", ["actor_profile_id"])

    op.create_table(
        "career_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("career_recommendation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(40), nullable=False),
        sa.Column("estimated_impact", sa.String(40), nullable=False),
        sa.Column("related_archetype", sa.String(120), nullable=False),
        sa.Column("target_roles", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(40), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["career_recommendation_id"], ["career_recommendations.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_career_tasks_career_recommendation_id", "career_tasks", ["career_recommendation_id"])
    op.create_index("ix_career_tasks_status", "career_tasks", ["status"])


def downgrade() -> None:
    op.drop_table("career_tasks")
    op.drop_table("career_recommendations")
    op.drop_table("learning_insights")
    op.drop_table("agent_recommendations")
    op.drop_index("ix_opportunities_normalized_key", table_name="opportunities")
    op.drop_column("opportunities", "audition_travel_hours")
    op.drop_column("opportunities", "audition_type")
    op.drop_column("opportunities", "is_duplicate")
    op.drop_column("opportunities", "source_reliability_score")
    op.drop_column("opportunities", "category")
    op.drop_column("opportunities", "normalized_key")
    op.drop_column("assets", "analysis_explanation")
    op.drop_column("assets", "analysis_status")
    op.drop_column("assets", "ai_suggested_archetypes")
    op.drop_column("assets", "ai_suggested_tags")

