"""focus modes and casting goals

Revision ID: 0018_focus_modes_casting_goals
Revises: 0017_work_local
Create Date: 2026-06-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0018_focus_modes_casting_goals"
down_revision: Union[str, None] = "0017_work_local"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "focus_mode_preferences",
        sa.Column("actor_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("active_mode", sa.String(length=80), server_default=sa.text("'Audition Mode'"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "active_mode IN ('Audition Mode', 'Career Building Mode', 'Casting Goals Mode', 'Relationship Mode', 'Analytics Mode')",
            name="ck_focus_mode_preferences_active_mode",
        ),
        sa.ForeignKeyConstraint(["actor_profile_id"], ["actor_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("actor_profile_id", name="uq_focus_mode_preferences_actor"),
    )
    op.create_index("ix_focus_mode_preferences_actor_profile_id", "focus_mode_preferences", ["actor_profile_id"])

    op.create_table(
        "casting_goals",
        sa.Column("actor_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("goal_type", sa.String(length=80), nullable=False),
        sa.Column("target_archetypes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("target_role_types", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("target_project_types", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("target_markets", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("target_casting_offices", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("target_deadline", sa.Date(), nullable=True),
        sa.Column("priority", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_profile_id"], ["actor_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_casting_goals_actor_profile_id", "casting_goals", ["actor_profile_id"])
    op.create_index("ix_casting_goals_status", "casting_goals", ["status"])
    op.create_index("ix_casting_goals_goal_type", "casting_goals", ["goal_type"])


def downgrade() -> None:
    op.drop_index("ix_casting_goals_goal_type", table_name="casting_goals")
    op.drop_index("ix_casting_goals_status", table_name="casting_goals")
    op.drop_index("ix_casting_goals_actor_profile_id", table_name="casting_goals")
    op.drop_table("casting_goals")
    op.drop_index("ix_focus_mode_preferences_actor_profile_id", table_name="focus_mode_preferences")
    op.drop_table("focus_mode_preferences")
