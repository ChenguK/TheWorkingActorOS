"""script and reel scene finder

Revision ID: 0050_script_scene_finder
Revises: 0049_actor_journal
Create Date: 2026-07-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0050_script_scene_finder"
down_revision: Union[str, None] = "0049_actor_journal"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "script_sources",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=True),
        sa.Column("source_type", sa.String(length=120), nullable=False),
        sa.Column("rights_status", sa.String(length=80), server_default="Unknown", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("approved", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "rights_status IN ('Public Domain', 'Royalty-Free', 'Original / User-Owned', 'Licensed', 'Permission Required', 'Unknown')",
            name="ck_script_sources_rights_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_script_sources_approved", "script_sources", ["approved"])
    op.create_index("ix_script_sources_rights_status", "script_sources", ["rights_status"])

    op.create_table(
        "scene_candidates",
        sa.Column("script_source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("career_task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("rights_status", sa.String(length=80), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("logline", sa.Text(), nullable=False),
        sa.Column("scene_brief", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("action_status", sa.String(length=80), server_default="Candidate", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "rights_status IN ('Public Domain', 'Royalty-Free', 'Original / User-Owned', 'Licensed', 'Permission Required', 'Unknown')",
            name="ck_scene_candidates_rights_status",
        ),
        sa.CheckConstraint(
            "action_status IN ('Candidate', 'Saved', 'Permission Requested', 'Original Brief')",
            name="ck_scene_candidates_action_status",
        ),
        sa.ForeignKeyConstraint(["career_task_id"], ["career_development_tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["script_source_id"], ["script_sources.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scene_candidates_career_task_id", "scene_candidates", ["career_task_id"])
    op.create_index("ix_scene_candidates_script_source_id", "scene_candidates", ["script_source_id"])
    op.create_index("ix_scene_candidates_action_status", "scene_candidates", ["action_status"])


def downgrade() -> None:
    op.drop_index("ix_scene_candidates_action_status", table_name="scene_candidates")
    op.drop_index("ix_scene_candidates_script_source_id", table_name="scene_candidates")
    op.drop_index("ix_scene_candidates_career_task_id", table_name="scene_candidates")
    op.drop_table("scene_candidates")
    op.drop_index("ix_script_sources_rights_status", table_name="script_sources")
    op.drop_index("ix_script_sources_approved", table_name="script_sources")
    op.drop_table("script_sources")
