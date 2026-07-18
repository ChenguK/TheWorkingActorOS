"""relationships self tapes journal

Revision ID: 0010_history
Revises: 0009_links
Create Date: 2026-06-23 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_history"
down_revision: str | None = "0009_links"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "actor_relationships",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role_title", sa.String(length=120), nullable=False),
        sa.Column("company_office", sa.String(length=255), nullable=True),
        sa.Column("projects", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("last_contact_date", sa.Date(), nullable=True),
        sa.Column("relationship_strength", sa.String(length=40), nullable=False, server_default="Warm"),
        sa.Column("linked_outcomes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "role_title IN ('Casting Director', 'Casting Office', 'Producer', 'Director', 'Writer', 'Agent', 'Manager', 'Coach')",
            name="ck_actor_relationships_role_title",
        ),
        sa.CheckConstraint(
            "relationship_strength IN ('Cold', 'Warm', 'Strong', 'Champion')",
            name="ck_actor_relationships_strength",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_actor_relationships_name", "actor_relationships", ["name"])
    op.create_index("ix_actor_relationships_role_title", "actor_relationships", ["role_title"])
    op.create_index("ix_actor_relationships_strength", "actor_relationships", ["relationship_strength"])

    op.create_table(
        "relationship_opportunities",
        sa.Column("relationship_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["relationship_id"], ["actor_relationships.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("relationship_id", "opportunity_id"),
    )
    op.create_table(
        "relationship_submissions",
        sa.Column("relationship_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["relationship_id"], ["actor_relationships.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("relationship_id", "submission_id"),
    )

    op.create_table(
        "self_tapes",
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("role_type", sa.String(length=120), nullable=True),
        sa.Column("archetypes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("linked_opportunity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("linked_submission_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("outcome", sa.String(length=80), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("date_created", sa.Date(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["linked_opportunity_id"], ["opportunities.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["linked_submission_id"], ["submissions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_self_tapes_role_type", "self_tapes", ["role_type"])
    op.create_index("ix_self_tapes_outcome", "self_tapes", ["outcome"])
    op.create_index("ix_self_tapes_date_created", "self_tapes", ["date_created"])

    op.create_table(
        "audition_journal_entries",
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("preparation_notes", sa.Text(), nullable=True),
        sa.Column("performance_notes", sa.Text(), nullable=True),
        sa.Column("casting_notes", sa.Text(), nullable=True),
        sa.Column("wardrobe_notes", sa.Text(), nullable=True),
        sa.Column("emotional_notes", sa.Text(), nullable=True),
        sa.Column("follow_up_notes", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audition_journal_entries_date", "audition_journal_entries", ["date"])
    op.create_index("ix_audition_journal_entries_opportunity_id", "audition_journal_entries", ["opportunity_id"])
    op.create_index("ix_audition_journal_entries_submission_id", "audition_journal_entries", ["submission_id"])


def downgrade() -> None:
    op.drop_index("ix_audition_journal_entries_submission_id", table_name="audition_journal_entries")
    op.drop_index("ix_audition_journal_entries_opportunity_id", table_name="audition_journal_entries")
    op.drop_index("ix_audition_journal_entries_date", table_name="audition_journal_entries")
    op.drop_table("audition_journal_entries")
    op.drop_index("ix_self_tapes_date_created", table_name="self_tapes")
    op.drop_index("ix_self_tapes_outcome", table_name="self_tapes")
    op.drop_index("ix_self_tapes_role_type", table_name="self_tapes")
    op.drop_table("self_tapes")
    op.drop_table("relationship_submissions")
    op.drop_table("relationship_opportunities")
    op.drop_index("ix_actor_relationships_strength", table_name="actor_relationships")
    op.drop_index("ix_actor_relationships_role_title", table_name="actor_relationships")
    op.drop_index("ix_actor_relationships_name", table_name="actor_relationships")
    op.drop_table("actor_relationships")
