"""platform profile import

Revision ID: 0012_platform
Revises: 0011_advanced
Create Date: 2026-06-23 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012_platform"
down_revision: str | None = "0011_advanced"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "platform_profiles",
        sa.Column("actor_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("platform_name", sa.String(length=120), nullable=False),
        sa.Column("profile_url", sa.String(length=1000), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("import_method", sa.String(length=80), nullable=False),
        sa.Column("raw_import_text", sa.Text(), nullable=False),
        sa.Column("import_status", sa.String(length=60), nullable=False, server_default="Draft"),
        sa.Column("user_approved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("parsed_profile", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "platform_name IN ('Actors Access', 'Casting Networks', 'Casting Frontier', 'Other')",
            name="ck_platform_profiles_platform_name",
        ),
        sa.CheckConstraint(
            "import_method IN ('Manual Copy/Paste', 'Uploaded PDF', 'Uploaded Screenshot', 'Uploaded CSV', 'User-Provided Text', 'Manual Guided Form')",
            name="ck_platform_profiles_import_method",
        ),
        sa.CheckConstraint(
            "import_status IN ('Draft', 'Needs Review', 'Approved', 'Rejected')",
            name="ck_platform_profiles_import_status",
        ),
        sa.ForeignKeyConstraint(["actor_profile_id"], ["actor_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_platform_profiles_actor_profile_id", "platform_profiles", ["actor_profile_id"])
    op.create_index("ix_platform_profiles_platform_name", "platform_profiles", ["platform_name"])
    op.create_index("ix_platform_profiles_import_status", "platform_profiles", ["import_status"])

    op.create_table(
        "platform_asset_mappings",
        sa.Column("platform_name", sa.String(length=120), nullable=False),
        sa.Column("platform_asset_name", sa.String(length=255), nullable=False),
        sa.Column("asset_type", sa.String(length=40), nullable=False),
        sa.Column("local_asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("archetypes", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "platform_name IN ('Actors Access', 'Casting Networks', 'Casting Frontier', 'Other')",
            name="ck_platform_asset_mappings_platform_name",
        ),
        sa.CheckConstraint(
            "asset_type IN ('Headshot', 'Reel', 'Slate', 'Resume', 'Other')",
            name="ck_platform_asset_mappings_asset_type",
        ),
        sa.ForeignKeyConstraint(["local_asset_id"], ["assets.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_platform_asset_mappings_platform_name", "platform_asset_mappings", ["platform_name"])
    op.create_index("ix_platform_asset_mappings_asset_type", "platform_asset_mappings", ["asset_type"])
    op.create_index("ix_platform_asset_mappings_local_asset_id", "platform_asset_mappings", ["local_asset_id"])


def downgrade() -> None:
    op.drop_index("ix_platform_asset_mappings_local_asset_id", table_name="platform_asset_mappings")
    op.drop_index("ix_platform_asset_mappings_asset_type", table_name="platform_asset_mappings")
    op.drop_index("ix_platform_asset_mappings_platform_name", table_name="platform_asset_mappings")
    op.drop_table("platform_asset_mappings")
    op.drop_index("ix_platform_profiles_import_status", table_name="platform_profiles")
    op.drop_index("ix_platform_profiles_platform_name", table_name="platform_profiles")
    op.drop_index("ix_platform_profiles_actor_profile_id", table_name="platform_profiles")
    op.drop_table("platform_profiles")
