"""executive intelligence and actor workflow records

Revision ID: 0035_executive_intelligence
Revises: 0034_role_prefs
Create Date: 2026-07-02 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0035_executive_intelligence"
down_revision: Union[str, None] = "0034_role_prefs"
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
        "career_memories",
        uuid_pk(),
        sa.Column("actor_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("current_career_goals", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("current_focus", sa.Text(), nullable=True),
        sa.Column("stretch_archetypes", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("preferred_project_types", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("preferred_markets", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("unavailable_dates", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("career_notes", sa.Text(), nullable=True),
        sa.Column("executive_notes", sa.Text(), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["actor_profile_id"], ["actor_profiles.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_career_memories_actor_profile_id", "career_memories", ["actor_profile_id"])

    op.create_table(
        "executive_briefs",
        uuid_pk(),
        sa.Column("actor_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("brief_type", sa.String(40), nullable=False, server_default="Weekly"),
        sa.Column("new_matching_breakdowns", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("submissions_completed", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("callbacks_received", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("bookings", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("materials_used", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("career_progress", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("recommended_priorities", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("summary", sa.Text(), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["actor_profile_id"], ["actor_profiles.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_executive_briefs_actor_profile_id", "executive_briefs", ["actor_profile_id"])

    op.create_table(
        "callback_events",
        uuid_pk(),
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_name", sa.String(120), nullable=False),
        sa.Column("event_type", sa.String(120), nullable=False, server_default="First Callback"),
        sa.Column("event_datetime", sa.Date(), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("is_virtual", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("preparation_notes", sa.Text(), nullable=True),
        sa.Column("outcome", sa.String(80), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_callback_events_submission_id", "callback_events", ["submission_id"])
    op.create_index("ix_callback_events_opportunity_id", "callback_events", ["opportunity_id"])

    op.create_table(
        "communication_logs",
        uuid_pk(),
        sa.Column("representation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("topic", sa.String(255), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("follow_up_needed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("follow_up_date", sa.Date(), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["representation_id"], ["representations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_communication_logs_representation_id", "communication_logs", ["representation_id"])
    op.create_index("ix_communication_logs_opportunity_id", "communication_logs", ["opportunity_id"])
    op.create_index("ix_communication_logs_submission_id", "communication_logs", ["submission_id"])

    op.create_table(
        "availability_blocks",
        uuid_pk(),
        sa.Column("actor_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("block_type", sa.String(80), nullable=False, server_default="Personal Commitment"),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["actor_profile_id"], ["actor_profiles.id"], ondelete="CASCADE"),
        sa.CheckConstraint("end_date >= start_date", name="ck_availability_blocks_date_order"),
    )
    op.create_index("ix_availability_blocks_actor_profile_id", "availability_blocks", ["actor_profile_id"])

    op.create_table(
        "professional_equipment_profiles",
        uuid_pk(),
        sa.Column("actor_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cameras", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("lighting", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("audio_equipment", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("backdrops", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("editing_software", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("teleprompter", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reader_availability", sa.String(255), nullable=True),
        sa.Column("internet_upload_speed", sa.String(120), nullable=True),
        sa.Column("home_audition_space", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["actor_profile_id"], ["actor_profiles.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_professional_equipment_profiles_actor_profile_id", "professional_equipment_profiles", ["actor_profile_id"])


def downgrade() -> None:
    op.drop_table("professional_equipment_profiles")
    op.drop_table("availability_blocks")
    op.drop_table("communication_logs")
    op.drop_table("callback_events")
    op.drop_table("executive_briefs")
    op.drop_table("career_memories")
