"""add script scene result type and material plan approval

Revision ID: 0053_script_scene_plan_gate
Revises: 0052_source_matched_breakdown
Create Date: 2026-07-13 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0053_script_scene_plan_gate"
down_revision: Union[str, None] = "0052_source_matched_breakdown"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "material_creation_plans",
        sa.Column("plan_status", sa.String(length=80), server_default="Pending Review", nullable=False),
    )
    op.create_check_constraint(
        "ck_material_creation_plans_plan_status",
        "material_creation_plans",
        "plan_status IN ('Pending Review', 'Approved', 'Denied')",
    )
    op.alter_column("material_creation_plans", "plan_status", server_default=None)

    op.add_column(
        "scene_candidates",
        sa.Column("result_type", sa.String(length=80), server_default="Specific Scene", nullable=False),
    )
    op.create_check_constraint(
        "ck_scene_candidates_result_type",
        "scene_candidates",
        "result_type IN ('Specific Scene', 'Specific Monologue', 'Script Library', 'Resource Guide', 'Music / Sound Library', 'Dead / Fetch Failed', 'Rights Unknown', 'Not Useful')",
    )
    op.alter_column("scene_candidates", "result_type", server_default=None)


def downgrade() -> None:
    op.drop_constraint("ck_scene_candidates_result_type", "scene_candidates", type_="check")
    op.drop_column("scene_candidates", "result_type")
    op.drop_constraint("ck_material_creation_plans_plan_status", "material_creation_plans", type_="check")
    op.drop_column("material_creation_plans", "plan_status")
