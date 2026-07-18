"""breakdown roles

Revision ID: 0028_breakdown_roles
Revises: 0027_source_research_soft_delete
Create Date: 2026-07-01 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0028_breakdown_roles"
down_revision: str | None = "0027_source_research_soft_delete"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "breakdown_roles",
        sa.Column("breakdown_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_name", sa.String(length=255), nullable=False),
        sa.Column("billing_or_role_type", sa.String(length=120), nullable=True),
        sa.Column("character_description", sa.Text(), nullable=True),
        sa.Column("gender_presentation", sa.String(length=160), nullable=True),
        sa.Column("ethnicity_or_cultural_background", sa.String(length=255), nullable=True),
        sa.Column("playable_age_min", sa.Integer(), nullable=True),
        sa.Column("playable_age_max", sa.Integer(), nullable=True),
        sa.Column("height_requirements", sa.String(length=255), nullable=True),
        sa.Column("vocal_requirements", sa.Text(), nullable=True),
        sa.Column("dance_requirements", sa.Text(), nullable=True),
        sa.Column("movement_requirements", sa.Text(), nullable=True),
        sa.Column("language_requirements", sa.Text(), nullable=True),
        sa.Column("special_skills", sa.Text(), nullable=True),
        sa.Column("union_status", sa.String(length=120), nullable=True),
        sa.Column("role_notes", sa.Text(), nullable=True),
        sa.Column("fit_status", sa.String(length=40), nullable=False, server_default="Needs Review"),
        sa.Column("fit_explanation", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "fit_status IN ('Strong Fit', 'Possible Fit', 'Stretch Fit', 'Not Fit', 'Needs Review')",
            name="ck_breakdown_roles_fit_status",
        ),
        sa.CheckConstraint(
            "playable_age_min IS NULL OR playable_age_max IS NULL OR playable_age_min <= playable_age_max",
            name="ck_breakdown_roles_playable_age_range",
        ),
        sa.ForeignKeyConstraint(["breakdown_id"], ["opportunities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_breakdown_roles_breakdown_id"), "breakdown_roles", ["breakdown_id"], unique=False)
    op.alter_column("breakdown_roles", "fit_status", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_breakdown_roles_breakdown_id"), table_name="breakdown_roles")
    op.drop_table("breakdown_roles")
