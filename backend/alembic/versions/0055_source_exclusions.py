"""add compact source exclusion memory

Revision ID: 0055_source_exclusions
Revises: 0054_protect_opportunity_delete
Create Date: 2026-07-18 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0055_source_exclusions"
down_revision: Union[str, None] = "0054_protect_opportunity_delete"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "source_exclusions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("source_name", sa.String(length=160), nullable=False),
        sa.Column("external_source_id", sa.String(length=255), nullable=True),
        sa.Column("canonical_url_hash", sa.String(length=64), nullable=True),
        sa.Column("content_version_hash", sa.String(length=64), nullable=False),
        sa.Column("exclusion_type", sa.String(length=40), nullable=False),
        sa.Column("classification", sa.String(length=80), nullable=False),
        sa.Column("reason_code", sa.String(length=80), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("times_seen", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "external_source_id IS NOT NULL OR canonical_url_hash IS NOT NULL",
            name="ck_source_exclusions_identity",
        ),
        sa.CheckConstraint(
            "external_source_id IS NOT NULL OR expires_at IS NOT NULL",
            name="ck_source_exclusions_weak_expiry",
        ),
        sa.CheckConstraint("times_seen >= 1", name="ck_source_exclusions_times_seen"),
        sa.CheckConstraint(
            "last_seen_at >= first_seen_at", name="ck_source_exclusions_seen_order"
        ),
        sa.CheckConstraint(
            "expires_at IS NULL OR expires_at > first_seen_at",
            name="ck_source_exclusions_expiry_order",
        ),
        sa.CheckConstraint(
            "exclusion_type IN ('confirmed_non_acting')",
            name="ck_source_exclusions_type",
        ),
        sa.CheckConstraint(
            "classification IN ('Crew Job', 'Non-Acting Job')",
            name="ck_source_exclusions_classification",
        ),
        sa.CheckConstraint(
            "reason_code IN ('provider_listing_rule', 'deterministic_classification')",
            name="ck_source_exclusions_reason",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_source_exclusions_source_external_id",
        "source_exclusions",
        ["source_name", "external_source_id"],
        unique=True,
        postgresql_where=sa.text("external_source_id IS NOT NULL"),
    )
    op.create_index(
        "uq_source_exclusions_source_url_hash",
        "source_exclusions",
        ["source_name", "canonical_url_hash"],
        unique=True,
        postgresql_where=sa.text("canonical_url_hash IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_source_exclusions_source_url_hash", table_name="source_exclusions")
    op.drop_index("uq_source_exclusions_source_external_id", table_name="source_exclusions")
    op.drop_table("source_exclusions")

