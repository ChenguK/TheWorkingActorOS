"""add travel estimate cache

Revision ID: 0044_travel_estimates
Revises: 0043_demo_breakdown_flag
Create Date: 2026-07-03 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0044_travel_estimates"
down_revision = "0043_demo_breakdown_flag"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "travel_estimates",
        sa.Column("origin_text", sa.String(length=500), nullable=False),
        sa.Column("destination_text", sa.String(length=500), nullable=False),
        sa.Column("origin_lat", sa.Float(), nullable=True),
        sa.Column("origin_lng", sa.Float(), nullable=True),
        sa.Column("destination_lat", sa.Float(), nullable=True),
        sa.Column("destination_lng", sa.Float(), nullable=True),
        sa.Column("drive_minutes", sa.Float(), nullable=True),
        sa.Column("drive_hours", sa.Float(), nullable=True),
        sa.Column("distance_miles", sa.Float(), nullable=True),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_travel_estimates_origin_destination",
        "travel_estimates",
        ["origin_text", "destination_text"],
    )


def downgrade() -> None:
    op.drop_index("ix_travel_estimates_origin_destination", table_name="travel_estimates")
    op.drop_table("travel_estimates")
