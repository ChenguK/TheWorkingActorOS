"""discovery submission automation

Revision ID: 0004_automation
Revises: 0003_career_development_tasks
Create Date: 2026-06-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_automation"
down_revision: str | None = "0003_career_development_tasks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("opportunities", sa.Column("visibility_status", sa.String(40), nullable=False, server_default="visible"))
    op.add_column("opportunities", sa.Column("hidden_reason", sa.Text(), nullable=True))
    op.add_column("opportunities", sa.Column("manual_review_required", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_check_constraint("ck_opportunities_visibility_status", "opportunities", "visibility_status IN ('visible', 'hidden')")
    op.create_index("ix_opportunities_visibility_status", "opportunities", ["visibility_status"])

    op.create_table(
        "discovery_source_plugins",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("priority_rank", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(80), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("implementation_key", sa.String(120), nullable=False),
        sa.Column("reliability_score", sa.Float(), nullable=False, server_default="0.7"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_discovery_source_plugins_priority_rank", "discovery_source_plugins", ["priority_rank"])

    op.create_table(
        "discovery_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("source_plugin_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(60), nullable=False, server_default="queued"),
        sa.Column("opportunities_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("opportunities_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("opportunities_hidden", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("run_payload", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["source_plugin_id"], ["discovery_source_plugins.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_discovery_runs_status", "discovery_runs", ["status"])

    op.create_table(
        "submission_automation_queue",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recommendation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("adapter_key", sa.String(120), nullable=False),
        sa.Column("submission_mode", sa.String(80), nullable=False),
        sa.Column("approval_status", sa.String(60), nullable=False, server_default="Pending Approval"),
        sa.Column("automation_status", sa.String(60), nullable=False, server_default="Prepared"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("prepared_payload", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("execution_log", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recommendation_id"], ["agent_recommendations.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_submission_automation_queue_approval_status", "submission_automation_queue", ["approval_status"])
    op.create_index("ix_submission_automation_queue_automation_status", "submission_automation_queue", ["automation_status"])


def downgrade() -> None:
    op.drop_table("submission_automation_queue")
    op.drop_table("discovery_runs")
    op.drop_table("discovery_source_plugins")
    op.drop_index("ix_opportunities_visibility_status", table_name="opportunities")
    op.drop_constraint("ck_opportunities_visibility_status", "opportunities")
    op.drop_column("opportunities", "manual_review_required")
    op.drop_column("opportunities", "hidden_reason")
    op.drop_column("opportunities", "visibility_status")
