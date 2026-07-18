"""representation resume agent auditions

Revision ID: 0014_rep_resume
Revises: 0013_public
Create Date: 2026-06-23 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014_rep_resume"
down_revision: str | None = "0013_public"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "representations",
        sa.Column("actor_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agency_name", sa.String(length=255), nullable=False),
        sa.Column("agent_name", sa.String(length=255), nullable=True),
        sa.Column("agent_email", sa.String(length=255), nullable=True),
        sa.Column("agent_phone", sa.String(length=80), nullable=True),
        sa.Column("agency_website", sa.String(length=1000), nullable=True),
        sa.Column("representation_type", sa.String(length=80), nullable=False),
        sa.Column("market", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "representation_type IN ('Theatrical', 'Commercial', 'Voiceover', 'Print', 'Manager', 'Other')",
            name="ck_representations_type",
        ),
        sa.ForeignKeyConstraint(["actor_profile_id"], ["actor_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_representations_actor_profile_id", "representations", ["actor_profile_id"])
    op.create_index("ix_representations_active", "representations", ["active"])

    op.create_table(
        "acting_credits",
        sa.Column("actor_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("section_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("section_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("highlighted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("project_title", sa.String(length=255), nullable=True),
        sa.Column("role_or_character", sa.String(length=255), nullable=True),
        sa.Column("role_type", sa.String(length=120), nullable=True),
        sa.Column("production_company", sa.String(length=255), nullable=True),
        sa.Column("network_or_distributor", sa.String(length=255), nullable=True),
        sa.Column("director", sa.String(length=255), nullable=True),
        sa.Column("episode_title", sa.String(length=255), nullable=True),
        sa.Column("season_episode", sa.String(length=80), nullable=True),
        sa.Column("year", sa.String(length=20), nullable=True),
        sa.Column("union_status", sa.String(length=80), nullable=True),
        sa.Column("class_or_program", sa.String(length=255), nullable=True),
        sa.Column("instructor", sa.String(length=255), nullable=True),
        sa.Column("institution", sa.String(length=255), nullable=True),
        sa.Column("skill_name", sa.String(length=255), nullable=True),
        sa.Column("skill_category", sa.String(length=120), nullable=True),
        sa.Column("proficiency", sa.String(length=80), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "category IN ('Television', 'Film', 'Commercial', 'Theater', 'New Media', 'Voiceover', "
            "'Industrial', 'Print', 'Training', 'Special Skills', 'Other')",
            name="ck_acting_credits_category",
        ),
        sa.ForeignKeyConstraint(["actor_profile_id"], ["actor_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_acting_credits_actor_profile_id", "acting_credits", ["actor_profile_id"])
    op.create_index("ix_acting_credits_category", "acting_credits", ["category"])
    op.create_index("ix_acting_credits_display_order", "acting_credits", ["section_order", "display_order"])

    op.add_column("opportunities", sa.Column("representation_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("opportunities", sa.Column("casting_contact_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("opportunities", sa.Column("source_type", sa.String(length=80), nullable=False, server_default="Manual Entry"))
    op.add_column("opportunities", sa.Column("platform", sa.String(length=120), nullable=True))
    op.add_column("opportunities", sa.Column("from_agent", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("opportunities", sa.Column("project_type", sa.String(length=120), nullable=True))
    op.add_column("opportunities", sa.Column("role_type", sa.String(length=120), nullable=True))
    op.add_column("opportunities", sa.Column("archetypes", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"))
    op.add_column("opportunities", sa.Column("rate", sa.String(length=255), nullable=True))
    op.add_column("opportunities", sa.Column("shoot_location", sa.String(length=255), nullable=True))
    op.add_column("opportunities", sa.Column("audition_location", sa.String(length=255), nullable=True))
    op.add_column("opportunities", sa.Column("callback_date", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_opportunities_representation_id",
        "opportunities",
        "representations",
        ["representation_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_opportunities_casting_contact_id",
        "opportunities",
        "casting_contacts",
        ["casting_contact_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "ck_opportunities_source_type",
        "opportunities",
        "source_type IN ('Platform Discovery', 'Agent Submission', 'Direct Email', 'Social Media', 'Production Website', 'Manual Entry', 'Other')",
    )
    op.create_index("ix_opportunities_source_type", "opportunities", ["source_type"])
    op.create_index("ix_opportunities_representation_id", "opportunities", ["representation_id"])


def downgrade() -> None:
    op.drop_index("ix_opportunities_representation_id", table_name="opportunities")
    op.drop_index("ix_opportunities_source_type", table_name="opportunities")
    op.drop_constraint("ck_opportunities_source_type", "opportunities", type_="check")
    op.drop_constraint("fk_opportunities_casting_contact_id", "opportunities", type_="foreignkey")
    op.drop_constraint("fk_opportunities_representation_id", "opportunities", type_="foreignkey")
    for column in [
        "callback_date",
        "audition_location",
        "shoot_location",
        "rate",
        "archetypes",
        "role_type",
        "project_type",
        "from_agent",
        "platform",
        "source_type",
        "casting_contact_id",
        "representation_id",
    ]:
        op.drop_column("opportunities", column)
    op.drop_index("ix_acting_credits_display_order", table_name="acting_credits")
    op.drop_index("ix_acting_credits_category", table_name="acting_credits")
    op.drop_index("ix_acting_credits_actor_profile_id", table_name="acting_credits")
    op.drop_table("acting_credits")
    op.drop_index("ix_representations_active", table_name="representations")
    op.drop_index("ix_representations_actor_profile_id", table_name="representations")
    op.drop_table("representations")
