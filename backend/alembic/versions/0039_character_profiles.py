"""character intelligence profiles

Revision ID: 0039_character_profiles
Revises: 0038_platform_defaults
Create Date: 2026-07-03 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0039_character_profiles"
down_revision: Union[str, None] = "0038_platform_defaults"
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
        "character_profiles",
        uuid_pk(),
        sa.Column("breakdown_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("breakdown_role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_name", sa.String(255), nullable=False),
        sa.Column("billing", sa.String(120), nullable=True),
        sa.Column("primary_archetypes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("secondary_archetypes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("personality_traits", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("emotional_traits", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("relationships", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("motivations", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("internal_conflict", sa.Text(), nullable=True),
        sa.Column("external_conflict", sa.Text(), nullable=True),
        sa.Column("emotional_arc", sa.Text(), nullable=True),
        sa.Column("genre", sa.String(160), nullable=True),
        sa.Column("comedic_level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("dramatic_level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("physical_requirements", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("vocal_requirements", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("movement_requirements", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("casting_language", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("recommended_materials", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        *timestamps(),
        sa.CheckConstraint("comedic_level >= 0 AND comedic_level <= 100", name="ck_character_profiles_comedic_level"),
        sa.CheckConstraint("dramatic_level >= 0 AND dramatic_level <= 100", name="ck_character_profiles_dramatic_level"),
        sa.ForeignKeyConstraint(["breakdown_id"], ["opportunities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["breakdown_role_id"], ["breakdown_roles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("breakdown_role_id", name="uq_character_profiles_breakdown_role_id"),
    )
    op.create_index("ix_character_profiles_breakdown_id", "character_profiles", ["breakdown_id"])
    op.create_index("ix_character_profiles_breakdown_role_id", "character_profiles", ["breakdown_role_id"])


def downgrade() -> None:
    op.drop_index("ix_character_profiles_breakdown_role_id", table_name="character_profiles")
    op.drop_index("ix_character_profiles_breakdown_id", table_name="character_profiles")
    op.drop_table("character_profiles")
