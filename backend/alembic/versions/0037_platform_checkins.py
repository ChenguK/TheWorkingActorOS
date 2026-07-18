"""platform subscriptions and daily check-ins

Revision ID: 0037_platform_checkins
Revises: 0036_chief_staff_visibility
Create Date: 2026-07-02 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0037_platform_checkins"
down_revision: Union[str, None] = "0036_chief_staff_visibility"
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
        "casting_platform_subscriptions",
        uuid_pk(),
        sa.Column("platform_name", sa.String(120), nullable=False),
        sa.Column("has_subscription", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("subscription_level", sa.String(120), nullable=True),
        sa.Column("monthly_cost", sa.Numeric(10, 2), nullable=True),
        sa.Column("annual_cost", sa.Numeric(10, 2), nullable=True),
        sa.Column("renewal_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *timestamps(),
        sa.UniqueConstraint("platform_name", name="uq_casting_platform_subscriptions_platform_name"),
    )
    op.create_table(
        "daily_platform_check_ins",
        uuid_pk(),
        sa.Column("platform_subscription_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("check_date", sa.Date(), nullable=False),
        sa.Column("timezone", sa.String(80), nullable=False, server_default="America/New_York"),
        sa.Column("checked_today", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(
            ["platform_subscription_id"],
            ["casting_platform_subscriptions.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "platform_subscription_id",
            "check_date",
            "timezone",
            name="uq_daily_platform_check_ins_platform_date_timezone",
        ),
    )
    op.create_index(
        "ix_daily_platform_check_ins_platform_subscription_id",
        "daily_platform_check_ins",
        ["platform_subscription_id"],
    )
    for platform in ["Actors Access", "Casting Networks", "Casting Frontier", "Backstage", "Other"]:
        op.execute(
            "INSERT INTO casting_platform_subscriptions "
            "(platform_name, has_subscription, active) "
            f"VALUES ('{platform}', false, true) "
            "ON CONFLICT (platform_name) DO NOTHING"
        )


def downgrade() -> None:
    op.drop_table("daily_platform_check_ins")
    op.drop_table("casting_platform_subscriptions")
