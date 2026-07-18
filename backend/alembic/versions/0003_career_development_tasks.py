"""career development tasks

Revision ID: 0003_career_development_tasks
Revises: 0002_agent_system
Create Date: 2026-06-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_career_development_tasks"
down_revision: str | None = "0002_agent_system"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "career_development_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(40), nullable=False, server_default="Medium"),
        sa.Column("status", sa.String(40), nullable=False, server_default="Not Started"),
        sa.Column("related_archetype", sa.String(120), nullable=True),
        sa.Column("target_role_types", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("estimated_impact", sa.String(40), nullable=False, server_default="Medium"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("supported_archetypes", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("created_by_agent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archetype_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("career_recommendation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint("priority IN ('Low', 'Medium', 'High')", name="ck_career_dev_tasks_priority"),
        sa.CheckConstraint("status IN ('Not Started', 'In Progress', 'Completed')", name="ck_career_dev_tasks_status"),
        sa.CheckConstraint("estimated_impact IN ('Low', 'Medium', 'High')", name="ck_career_dev_tasks_impact"),
        sa.ForeignKeyConstraint(["archetype_id"], ["archetypes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["career_recommendation_id"], ["career_recommendations.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_career_development_tasks_status", "career_development_tasks", ["status"])
    op.create_index("ix_career_development_tasks_priority", "career_development_tasks", ["priority"])
    op.create_index("ix_career_development_tasks_related_archetype", "career_development_tasks", ["related_archetype"])
    op.create_index("ix_career_development_tasks_created_by_agent", "career_development_tasks", ["created_by_agent"])


def downgrade() -> None:
    op.drop_table("career_development_tasks")

