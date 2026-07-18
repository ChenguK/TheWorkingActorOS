"""public profile import

Revision ID: 0013_public
Revises: 0012_platform
Create Date: 2026-06-23 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013_public"
down_revision: str | None = "0012_platform"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "public_profile_imports",
        sa.Column("platform_name", sa.String(length=120), nullable=False),
        sa.Column("profile_url", sa.String(length=1000), nullable=False),
        sa.Column("import_method", sa.String(length=80), nullable=False, server_default="Public/shareable profile URL"),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_visible_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("parsed_data_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("import_status", sa.String(length=60), nullable=False, server_default="Draft"),
        sa.Column("user_approved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "platform_name IN ('Actors Access', 'Casting Networks', 'Casting Frontier', 'Other')",
            name="ck_public_profile_imports_platform_name",
        ),
        sa.CheckConstraint(
            "import_method = 'Public/shareable profile URL'",
            name="ck_public_profile_imports_import_method",
        ),
        sa.CheckConstraint(
            "import_status IN ('Draft', 'Needs Review', 'Approved', 'Rejected', 'Blocked')",
            name="ck_public_profile_imports_import_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_public_profile_imports_platform_name", "public_profile_imports", ["platform_name"])
    op.create_index("ix_public_profile_imports_import_status", "public_profile_imports", ["import_status"])
    op.create_index("ix_public_profile_imports_imported_at", "public_profile_imports", ["imported_at"])


def downgrade() -> None:
    op.drop_index("ix_public_profile_imports_imported_at", table_name="public_profile_imports")
    op.drop_index("ix_public_profile_imports_import_status", table_name="public_profile_imports")
    op.drop_index("ix_public_profile_imports_platform_name", table_name="public_profile_imports")
    op.drop_table("public_profile_imports")
