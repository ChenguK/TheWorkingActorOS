"""dashboard widgets

Revision ID: 0015_dashboard
Revises: 0014_rep_resume
Create Date: 2026-06-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015_dashboard"
down_revision: str | None = "0014_rep_resume"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dashboard_widgets",
        sa.Column("actor_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("widget_id", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=180), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("size", sa.String(length=20), server_default=sa.text("'medium'"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("size IN ('small', 'medium', 'large')", name="ck_dashboard_widgets_size"),
        sa.ForeignKeyConstraint(["actor_profile_id"], ["actor_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("actor_profile_id", "widget_id", name="uq_dashboard_widgets_actor_widget"),
    )
    op.create_index("ix_dashboard_widgets_actor_profile_id", "dashboard_widgets", ["actor_profile_id"])
    op.create_index("ix_dashboard_widgets_widget_id", "dashboard_widgets", ["widget_id"])
    op.create_index("ix_dashboard_widgets_sort_order", "dashboard_widgets", ["sort_order"])


def downgrade() -> None:
    op.drop_index("ix_dashboard_widgets_sort_order", table_name="dashboard_widgets")
    op.drop_index("ix_dashboard_widgets_widget_id", table_name="dashboard_widgets")
    op.drop_index("ix_dashboard_widgets_actor_profile_id", table_name="dashboard_widgets")
    op.drop_table("dashboard_widgets")
