"""add manual override logs

Revision ID: 0048_manual_overrides
Revises: 0047_source_verify
Create Date: 2026-07-04 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0048_manual_overrides"
down_revision = "0047_source_verify"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "manual_override_logs",
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("field_name", sa.String(length=160), nullable=False),
        sa.Column("previous_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("new_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("changed_by", sa.String(length=80), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_manual_override_logs_entity_type", "manual_override_logs", ["entity_type"])
    op.create_index("ix_manual_override_logs_entity_id", "manual_override_logs", ["entity_id"])


def downgrade() -> None:
    op.drop_index("ix_manual_override_logs_entity_id", table_name="manual_override_logs")
    op.drop_index("ix_manual_override_logs_entity_type", table_name="manual_override_logs")
    op.drop_table("manual_override_logs")
