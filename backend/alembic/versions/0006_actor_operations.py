"""actor operations layer

Revision ID: 0006_ops
Revises: 0005_command
Create Date: 2026-06-22 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0006_ops"
down_revision: Union[str, None] = "0005_command"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("opportunities", sa.Column("hidden_by_rule", sa.String(length=120), nullable=True))
    op.add_column("opportunities", sa.Column("audition_drive_time", sa.Float(), nullable=True))
    op.create_index("ix_opportunities_hidden_by_rule", "opportunities", ["hidden_by_rule"])

    for column_name in [
        "submission_fee",
        "media_fee",
        "travel_cost",
        "housing_cost",
        "parking_cost",
        "other_cost",
        "total_cost",
    ]:
        op.add_column(
            "submissions",
            sa.Column(column_name, sa.Numeric(10, 2), server_default="0", nullable=False),
        )

    op.add_column("assets", sa.Column("upload_date", sa.Date(), nullable=True))
    op.add_column("assets", sa.Column("last_used_date", sa.Date(), nullable=True))
    op.add_column("assets", sa.Column("last_updated_date", sa.Date(), nullable=True))
    op.add_column("assets", sa.Column("expiration_warning_date", sa.Date(), nullable=True))
    op.add_column(
        "assets",
        sa.Column("freshness_status", sa.String(length=40), server_default="Current", nullable=False),
    )
    op.create_index("ix_assets_freshness_status", "assets", ["freshness_status"])
    op.create_check_constraint(
        "ck_assets_freshness_status",
        "assets",
        "freshness_status IN ('Current', 'Aging', 'Needs Review', 'Outdated')",
    )

    op.create_table(
        "audition_calendar_events",
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("start_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_datetime", sa.DateTime(timezone=True), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("is_virtual", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('Submission Due', 'Self-Tape Due', 'Virtual Callback', "
            "'In-Person Callback', 'Fitting', 'Shoot', 'Meeting', 'Other')",
            name="ck_audition_calendar_events_type",
        ),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audition_calendar_events_start", "audition_calendar_events", ["start_datetime"])
    op.create_index("ix_audition_calendar_events_type", "audition_calendar_events", ["event_type"])


def downgrade() -> None:
    op.drop_index("ix_audition_calendar_events_type", table_name="audition_calendar_events")
    op.drop_index("ix_audition_calendar_events_start", table_name="audition_calendar_events")
    op.drop_table("audition_calendar_events")

    op.drop_constraint("ck_assets_freshness_status", "assets", type_="check")
    op.drop_index("ix_assets_freshness_status", table_name="assets")
    op.drop_column("assets", "freshness_status")
    op.drop_column("assets", "expiration_warning_date")
    op.drop_column("assets", "last_updated_date")
    op.drop_column("assets", "last_used_date")
    op.drop_column("assets", "upload_date")

    for column_name in [
        "total_cost",
        "other_cost",
        "parking_cost",
        "housing_cost",
        "travel_cost",
        "media_fee",
        "submission_fee",
    ]:
        op.drop_column("submissions", column_name)

    op.drop_index("ix_opportunities_hidden_by_rule", table_name="opportunities")
    op.drop_column("opportunities", "audition_drive_time")
    op.drop_column("opportunities", "hidden_by_rule")
