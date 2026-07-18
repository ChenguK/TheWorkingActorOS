"""phase 1 schema

Revision ID: 0001_phase_1_schema
Revises:
Create Date: 2026-06-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_phase_1_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "actor_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("sag_status", sa.String(100), nullable=False),
        sa.Column("union_status", sa.String(100), nullable=False),
        sa.Column("current_location", sa.String(255), nullable=False),
        sa.Column("playable_age_min", sa.Integer(), nullable=False),
        sa.Column("playable_age_max", sa.Integer(), nullable=False),
        sa.Column("secondary_playable_age_min", sa.Integer(), nullable=True),
        sa.Column("secondary_playable_age_max", sa.Integer(), nullable=True),
        sa.Column("skills", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("playable_age_min <= playable_age_max", name="ck_actor_primary_age_range"),
        sa.CheckConstraint(
            "secondary_playable_age_min IS NULL OR secondary_playable_age_max IS NULL "
            "OR secondary_playable_age_min <= secondary_playable_age_max",
            name="ck_actor_secondary_age_range",
        ),
    )

    op.create_table(
        "travel_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("actor_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("max_local_drive_time", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("extended_drive_time", sa.Integer(), nullable=False, server_default="720"),
        sa.Column("flight_allowed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("housing_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("international_allowed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_profile_id"], ["actor_profiles.id"], ondelete="CASCADE"),
        sa.CheckConstraint("max_local_drive_time > 0", name="ck_travel_max_drive_positive"),
        sa.CheckConstraint("extended_drive_time >= max_local_drive_time", name="ck_travel_extended_gte_local"),
    )
    op.create_index("ix_travel_preferences_actor_profile_id", "travel_preferences", ["actor_profile_id"])

    op.create_table(
        "archetypes",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(140), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_archetypes_slug", "archetypes", ["slug"])

    op.create_table(
        "assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("actor_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_name", sa.String(255), nullable=False),
        sa.Column("asset_type", sa.String(40), nullable=False),
        sa.Column("local_file_path", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=True),
        sa.Column("mime_type", sa.String(120), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("archetype_names", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_profile_id"], ["actor_profiles.id"], ondelete="CASCADE"),
        sa.CheckConstraint("asset_type IN ('Headshot', 'Reel', 'Slate', 'Resume')", name="ck_assets_type"),
    )
    op.create_index("ix_assets_actor_profile_id", "assets", ["actor_profile_id"])
    op.create_index("ix_assets_asset_type", "assets", ["asset_type"])

    op.create_table(
        "asset_tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tag", sa.String(120), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("asset_id", "tag", name="uq_asset_tags_asset_tag"),
    )
    op.create_index("ix_asset_tags_asset_id", "asset_tags", ["asset_id"])
    op.create_index("ix_asset_tags_tag", "asset_tags", ["tag"])

    op.create_table(
        "asset_archetypes",
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("archetype_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["archetype_id"], ["archetypes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("asset_id", "archetype_id"),
    )

    op.create_table(
        "opportunity_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("source_type", sa.String(80), nullable=False, server_default="manual"),
        sa.Column("priority_rank", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "opportunities",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("opportunity_source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("role", sa.String(255), nullable=False),
        sa.Column("project", sa.String(255), nullable=False),
        sa.Column("union", sa.String(80), nullable=False),
        sa.Column("location", sa.String(255), nullable=False),
        sa.Column("travel_covered", sa.Boolean(), nullable=True),
        sa.Column("housing_covered", sa.Boolean(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(60), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["opportunity_source_id"], ["opportunity_sources.id"], ondelete="SET NULL"),
        sa.CheckConstraint("status IN ('open', 'closed', 'archived')", name="ck_opportunities_status"),
    )
    op.create_index("ix_opportunities_role", "opportunities", ["role"])
    op.create_index("ix_opportunities_project", "opportunities", ["project"])
    op.create_index("ix_opportunities_status", "opportunities", ["status"])

    op.create_table(
        "submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("actor_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("current_status", sa.String(80), nullable=False, server_default="Submitted"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_profile_id"], ["actor_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "current_status IN ('Submitted', 'Requested', 'Self-Tape Callback', 'In-Person Callback', "
            "'Pinned', 'Booked', 'Passed', 'No Response')",
            name="ck_submissions_current_status",
        ),
    )
    op.create_index("ix_submissions_actor_profile_id", "submissions", ["actor_profile_id"])
    op.create_index("ix_submissions_opportunity_id", "submissions", ["opportunity_id"])
    op.create_index("ix_submissions_current_status", "submissions", ["current_status"])

    op.create_table(
        "submission_assets",
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("submission_id", "asset_id"),
    )

    op.create_table(
        "submission_status_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(80), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "status IN ('Submitted', 'Requested', 'Self-Tape Callback', 'In-Person Callback', "
            "'Pinned', 'Booked', 'Passed', 'No Response')",
            name="ck_submission_status_history_status",
        ),
    )
    op.create_index("ix_submission_status_submission_id", "submission_status_history", ["submission_id"])
    op.create_index("ix_submission_status_status", "submission_status_history", ["status"])


def downgrade() -> None:
    op.drop_table("submission_status_history")
    op.drop_table("submission_assets")
    op.drop_table("submissions")
    op.drop_table("opportunities")
    op.drop_table("opportunity_sources")
    op.drop_table("asset_archetypes")
    op.drop_table("asset_tags")
    op.drop_table("assets")
    op.drop_table("archetypes")
    op.drop_table("travel_preferences")
    op.drop_table("actor_profiles")
