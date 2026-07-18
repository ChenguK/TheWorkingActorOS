"""add actor journal entries

Revision ID: 0049_actor_journal
Revises: 0048_manual_overrides
Create Date: 2026-07-05 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0049_actor_journal"
down_revision = "0048_manual_overrides"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "actor_journal_entries",
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("linked_breakdown_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("linked_audition_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("linked_material_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("linked_career_task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["linked_audition_id"], ["submissions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["linked_breakdown_id"], ["opportunities.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["linked_career_task_id"], ["career_development_tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["linked_material_id"], ["assets.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_actor_journal_entries_date", "actor_journal_entries", ["date"])
    op.create_index("ix_actor_journal_entries_event_type", "actor_journal_entries", ["event_type"])
    op.create_index("ix_actor_journal_entries_linked_audition_id", "actor_journal_entries", ["linked_audition_id"])
    op.create_index("ix_actor_journal_entries_linked_breakdown_id", "actor_journal_entries", ["linked_breakdown_id"])
    op.create_index("ix_actor_journal_entries_linked_career_task_id", "actor_journal_entries", ["linked_career_task_id"])
    op.create_index("ix_actor_journal_entries_linked_material_id", "actor_journal_entries", ["linked_material_id"])


def downgrade() -> None:
    op.drop_index("ix_actor_journal_entries_linked_material_id", table_name="actor_journal_entries")
    op.drop_index("ix_actor_journal_entries_linked_career_task_id", table_name="actor_journal_entries")
    op.drop_index("ix_actor_journal_entries_linked_breakdown_id", table_name="actor_journal_entries")
    op.drop_index("ix_actor_journal_entries_linked_audition_id", table_name="actor_journal_entries")
    op.drop_index("ix_actor_journal_entries_event_type", table_name="actor_journal_entries")
    op.drop_index("ix_actor_journal_entries_date", table_name="actor_journal_entries")
    op.drop_table("actor_journal_entries")
