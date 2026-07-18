"""discovery limits

Revision ID: 0033_discovery_limits
Revises: 0032_facts_inference_split
Create Date: 2026-07-01 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0033_discovery_limits"
down_revision: str | None = "0032_facts_inference_split"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "discovery_settings",
        sa.Column("film_tv_breakdown_limit", sa.Integer(), nullable=False, server_default="25"),
        sa.Column("theater_breakdown_limit", sa.Integer(), nullable=False, server_default="25"),
        sa.Column("commercial_breakdown_limit", sa.Integer(), nullable=False, server_default="25"),
        sa.Column("voiceover_breakdown_limit", sa.Integer(), nullable=False, server_default="25"),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("film_tv_breakdown_limit >= 0", name="ck_discovery_settings_film_tv_limit"),
        sa.CheckConstraint("theater_breakdown_limit >= 0", name="ck_discovery_settings_theater_limit"),
        sa.CheckConstraint("commercial_breakdown_limit >= 0", name="ck_discovery_settings_commercial_limit"),
        sa.CheckConstraint("voiceover_breakdown_limit >= 0", name="ck_discovery_settings_voiceover_limit"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.alter_column("discovery_settings", "film_tv_breakdown_limit", server_default=None)
    op.alter_column("discovery_settings", "theater_breakdown_limit", server_default=None)
    op.alter_column("discovery_settings", "commercial_breakdown_limit", server_default=None)
    op.alter_column("discovery_settings", "voiceover_breakdown_limit", server_default=None)


def downgrade() -> None:
    op.drop_table("discovery_settings")
