"""supervised breakdown imports

Revision ID: 0019_supervised_breakdowns
Revises: 0018_focus_modes_casting_goals
Create Date: 2026-06-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0019_supervised_breakdowns"
down_revision: str | None = "0018_focus_modes_casting_goals"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "supervised_breakdown_imports",
        sa.Column("actor_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_opportunity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("platform_name", sa.String(length=120), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_visible_text", sa.Text(), server_default="", nullable=False),
        sa.Column("parsed_data_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("import_status", sa.String(length=60), server_default="Draft", nullable=False),
        sa.Column("user_approved", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "platform_name IN ('Actors Access', 'Casting Networks', 'Casting Frontier')",
            name="ck_supervised_breakdown_imports_platform_name",
        ),
        sa.CheckConstraint(
            "import_status IN ('Draft', 'Approved', 'Rejected', 'Needs Review', 'Blocked')",
            name="ck_supervised_breakdown_imports_import_status",
        ),
        sa.ForeignKeyConstraint(["actor_profile_id"], ["actor_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approved_opportunity_id"], ["opportunities.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_supervised_breakdown_imports_import_status",
        "supervised_breakdown_imports",
        ["import_status"],
    )
    op.create_index(
        "ix_supervised_breakdown_imports_platform_name",
        "supervised_breakdown_imports",
        ["platform_name"],
    )


def downgrade() -> None:
    op.drop_index("ix_supervised_breakdown_imports_platform_name", table_name="supervised_breakdown_imports")
    op.drop_index("ix_supervised_breakdown_imports_import_status", table_name="supervised_breakdown_imports")
    op.drop_table("supervised_breakdown_imports")
