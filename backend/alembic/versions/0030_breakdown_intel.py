"""breakdown intelligence engine

Revision ID: 0030_breakdown_intel
Revises: 0029_discovery_modes
Create Date: 2026-07-01 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0030_breakdown_intel"
down_revision: str | None = "0029_discovery_modes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "breakdown_sections",
        sa.Column("breakdown_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("section_type", sa.String(length=80), nullable=False),
        sa.Column("heading", sa.String(length=255), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("parsed_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("confidence_score", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "section_type IN ('Production Details', 'Audition Information', 'Preparation', 'Roles', "
            "'Character Descriptions', 'Dates', 'Locations', 'Submission Instructions', 'Contact', 'Additional Notes')",
            name="ck_breakdown_sections_section_type",
        ),
        sa.CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 100",
            name="ck_breakdown_sections_confidence_score",
        ),
        sa.ForeignKeyConstraint(["breakdown_id"], ["opportunities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_breakdown_sections_breakdown_id"), "breakdown_sections", ["breakdown_id"], unique=False)
    op.create_table(
        "breakdown_parse_runs",
        sa.Column("breakdown_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parser_version", sa.String(length=80), nullable=False, server_default="breakdown-intelligence-v1"),
        sa.Column("parse_mode", sa.String(length=80), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=60), nullable=False, server_default="running"),
        sa.Column("overall_confidence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "parse_mode IN ('Standard Parse', 'Deep Parse', 'Manual Paste Reparse')",
            name="ck_breakdown_parse_runs_parse_mode",
        ),
        sa.CheckConstraint("status IN ('running', 'succeeded', 'failed')", name="ck_breakdown_parse_runs_status"),
        sa.CheckConstraint(
            "overall_confidence >= 0 AND overall_confidence <= 100",
            name="ck_breakdown_parse_runs_overall_confidence",
        ),
        sa.ForeignKeyConstraint(["breakdown_id"], ["opportunities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_breakdown_parse_runs_breakdown_id"), "breakdown_parse_runs", ["breakdown_id"], unique=False)
    op.alter_column("breakdown_sections", "confidence_score", server_default=None)
    op.alter_column("breakdown_sections", "display_order", server_default=None)
    op.alter_column("breakdown_parse_runs", "parser_version", server_default=None)
    op.alter_column("breakdown_parse_runs", "status", server_default=None)
    op.alter_column("breakdown_parse_runs", "overall_confidence", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_breakdown_parse_runs_breakdown_id"), table_name="breakdown_parse_runs")
    op.drop_table("breakdown_parse_runs")
    op.drop_index(op.f("ix_breakdown_sections_breakdown_id"), table_name="breakdown_sections")
    op.drop_table("breakdown_sections")
