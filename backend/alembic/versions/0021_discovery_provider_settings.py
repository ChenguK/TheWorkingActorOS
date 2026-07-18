"""discovery provider settings

Revision ID: 0021_discovery_settings
Revises: 0020_demographics
Create Date: 2026-06-26 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0021_discovery_settings"
down_revision: str | None = "0020_demographics"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "discovery_provider_settings",
        sa.Column("provider_key", sa.String(length=160), nullable=False),
        sa.Column("display_name", sa.String(length=180), nullable=False),
        sa.Column("tier", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=False),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("poll_frequency_minutes", sa.Integer(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("authentication_method", sa.String(length=120), nullable=False),
        sa.Column("supported_authentication_methods", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reliability_score", sa.Float(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("provider_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("health_status", sa.String(length=80), nullable=False),
        sa.Column("health_message", sa.Text(), nullable=True),
        sa.Column("last_health_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("poll_frequency_minutes >= 0", name="ck_discovery_provider_settings_poll_frequency"),
        sa.CheckConstraint("priority >= 0", name="ck_discovery_provider_settings_priority"),
        sa.CheckConstraint(
            "reliability_score >= 0 AND reliability_score <= 1",
            name="ck_discovery_provider_settings_reliability",
        ),
        sa.CheckConstraint("tier >= 1 AND tier <= 5", name="ck_discovery_provider_settings_tier"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_key"),
    )
    op.create_index(
        op.f("ix_discovery_provider_settings_provider_key"),
        "discovery_provider_settings",
        ["provider_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_discovery_provider_settings_provider_key"), table_name="discovery_provider_settings")
    op.drop_table("discovery_provider_settings")
