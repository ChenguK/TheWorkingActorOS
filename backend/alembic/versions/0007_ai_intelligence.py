"""ai intelligence expansion

Revision ID: 0007_intel
Revises: 0006_ops
Create Date: 2026-06-22 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0007_intel"
down_revision: Union[str, None] = "0006_ops"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "casting_offices",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("source_platform", sa.String(length=120), nullable=True),
        sa.Column("project_history", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("submission_history", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("callback_history", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("booking_history", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_casting_offices_name", "casting_offices", ["name"])

    op.create_table(
        "casting_contacts",
        sa.Column("casting_office_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=120), server_default="Casting Director", nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["casting_office_id"], ["casting_offices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_casting_contacts_office", "casting_contacts", ["casting_office_id"])

    op.add_column("opportunities", sa.Column("casting_office_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_opportunities_casting_office_id",
        "opportunities",
        "casting_offices",
        ["casting_office_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_opportunities_casting_office_id", "opportunities", ["casting_office_id"])

    op.create_table(
        "audition_preparation_briefs",
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("brief", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "material_creation_plans",
        sa.Column("career_task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("missing_asset", sa.String(length=255), nullable=False),
        sa.Column("target_archetype", sa.String(length=120), nullable=True),
        sa.Column("plan", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["career_task_id"], ["career_development_tasks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "career_path_simulations",
        sa.Column("actor_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_profile_id"], ["actor_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("career_path_simulations")
    op.drop_table("material_creation_plans")
    op.drop_table("audition_preparation_briefs")
    op.drop_index("ix_opportunities_casting_office_id", table_name="opportunities")
    op.drop_constraint("fk_opportunities_casting_office_id", "opportunities", type_="foreignkey")
    op.drop_column("opportunities", "casting_office_id")
    op.drop_index("ix_casting_contacts_office", table_name="casting_contacts")
    op.drop_table("casting_contacts")
    op.drop_index("ix_casting_offices_name", table_name="casting_offices")
    op.drop_table("casting_offices")
