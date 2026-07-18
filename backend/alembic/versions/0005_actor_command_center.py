"""actor command center intelligence

Revision ID: 0005_command
Revises: 0004_automation
Create Date: 2026-06-22 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0005_command"
down_revision: Union[str, None] = "0004_automation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("opportunities", sa.Column("submission_deadline", sa.DateTime(timezone=True), nullable=True))
    op.add_column("opportunities", sa.Column("audition_deadline", sa.DateTime(timezone=True), nullable=True))
    op.add_column("opportunities", sa.Column("shoot_start_date", sa.Date(), nullable=True))
    op.add_column("opportunities", sa.Column("shoot_end_date", sa.Date(), nullable=True))
    op.add_column(
        "opportunities", sa.Column("priority", sa.String(length=40), server_default="Medium", nullable=False)
    )
    op.add_column("opportunities", sa.Column("urgency_score", sa.Integer(), server_default="0", nullable=False))
    op.add_column("opportunities", sa.Column("quality_score", sa.Integer(), server_default="50", nullable=False))
    op.add_column("opportunities", sa.Column("quality_explanation", sa.Text(), nullable=True))
    op.add_column(
        "opportunities", sa.Column("confidence_level", sa.String(length=40), server_default="Medium", nullable=False)
    )
    op.add_column(
        "opportunities", sa.Column("risk_level", sa.String(length=40), server_default="Medium", nullable=False)
    )
    op.add_column("opportunities", sa.Column("risk_explanation", sa.Text(), nullable=True))
    op.create_index("ix_opportunities_submission_deadline", "opportunities", ["submission_deadline"])
    op.create_index("ix_opportunities_audition_deadline", "opportunities", ["audition_deadline"])
    op.create_index("ix_opportunities_priority", "opportunities", ["priority"])
    op.create_check_constraint(
        "ck_opportunities_priority", "opportunities", "priority IN ('Low', 'Medium', 'High', 'Urgent')"
    )
    op.create_check_constraint(
        "ck_opportunities_urgency_score", "opportunities", "urgency_score >= 0 AND urgency_score <= 100"
    )
    op.create_check_constraint(
        "ck_opportunities_quality_score", "opportunities", "quality_score >= 0 AND quality_score <= 100"
    )
    op.create_check_constraint(
        "ck_opportunities_confidence_level",
        "opportunities",
        "confidence_level IN ('Low', 'Medium', 'High')",
    )
    op.create_check_constraint(
        "ck_opportunities_risk_level", "opportunities", "risk_level IN ('Low', 'Medium', 'High')"
    )

    op.add_column(
        "agent_recommendations",
        sa.Column("confidence_level", sa.String(length=40), server_default="Medium", nullable=False),
    )
    op.add_column(
        "agent_recommendations",
        sa.Column("risk_level", sa.String(length=40), server_default="Medium", nullable=False),
    )
    op.add_column("agent_recommendations", sa.Column("risk_explanation", sa.Text(), nullable=True))

    op.create_table(
        "self_tape_workflows",
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=40), server_default="Not Started", nullable=False),
        sa.Column("sides_file_path", sa.String(length=500), nullable=True),
        sa.Column("reader_needed", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("tape_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("slate_requirements", sa.Text(), nullable=True),
        sa.Column("wardrobe_notes", sa.Text(), nullable=True),
        sa.Column("upload_link", sa.String(length=500), nullable=True),
        sa.Column("final_file_path", sa.String(length=500), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_self_tape_workflows_status", "self_tape_workflows", ["status"])
    op.create_index("ix_self_tape_workflows_tape_due_at", "self_tape_workflows", ["tape_due_at"])

    op.create_table(
        "outcome_nudges",
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nudge_type", sa.String(length=80), server_default="Follow Up", nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), server_default="Open", nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_outcome_nudges_status", "outcome_nudges", ["status"])
    op.create_index("ix_outcome_nudges_due_at", "outcome_nudges", ["due_at"])

    op.create_table(
        "material_gap_alerts",
        sa.Column("actor_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("archetype", sa.String(length=120), nullable=False),
        sa.Column("gap_type", sa.String(length=80), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(length=40), server_default="Medium", nullable=False),
        sa.Column("status", sa.String(length=40), server_default="Open", nullable=False),
        sa.Column("recommended_action", sa.Text(), nullable=False),
        sa.Column("created_by_agent", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_profile_id"], ["actor_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_material_gap_alerts_status", "material_gap_alerts", ["status"])
    op.create_index("ix_material_gap_alerts_priority", "material_gap_alerts", ["priority"])


def downgrade() -> None:
    op.drop_index("ix_material_gap_alerts_priority", table_name="material_gap_alerts")
    op.drop_index("ix_material_gap_alerts_status", table_name="material_gap_alerts")
    op.drop_table("material_gap_alerts")
    op.drop_index("ix_outcome_nudges_due_at", table_name="outcome_nudges")
    op.drop_index("ix_outcome_nudges_status", table_name="outcome_nudges")
    op.drop_table("outcome_nudges")
    op.drop_index("ix_self_tape_workflows_tape_due_at", table_name="self_tape_workflows")
    op.drop_index("ix_self_tape_workflows_status", table_name="self_tape_workflows")
    op.drop_table("self_tape_workflows")

    op.drop_column("agent_recommendations", "risk_explanation")
    op.drop_column("agent_recommendations", "risk_level")
    op.drop_column("agent_recommendations", "confidence_level")

    op.drop_constraint("ck_opportunities_risk_level", "opportunities", type_="check")
    op.drop_constraint("ck_opportunities_confidence_level", "opportunities", type_="check")
    op.drop_constraint("ck_opportunities_quality_score", "opportunities", type_="check")
    op.drop_constraint("ck_opportunities_urgency_score", "opportunities", type_="check")
    op.drop_constraint("ck_opportunities_priority", "opportunities", type_="check")
    op.drop_index("ix_opportunities_priority", table_name="opportunities")
    op.drop_index("ix_opportunities_audition_deadline", table_name="opportunities")
    op.drop_index("ix_opportunities_submission_deadline", table_name="opportunities")
    op.drop_column("opportunities", "risk_explanation")
    op.drop_column("opportunities", "risk_level")
    op.drop_column("opportunities", "confidence_level")
    op.drop_column("opportunities", "quality_explanation")
    op.drop_column("opportunities", "quality_score")
    op.drop_column("opportunities", "urgency_score")
    op.drop_column("opportunities", "priority")
    op.drop_column("opportunities", "shoot_end_date")
    op.drop_column("opportunities", "shoot_start_date")
    op.drop_column("opportunities", "audition_deadline")
    op.drop_column("opportunities", "submission_deadline")
