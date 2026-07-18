"""protect opportunities that have submission history

Revision ID: 0054_protect_opportunity_delete
Revises: 0053_script_scene_plan_gate
Create Date: 2026-07-17 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0054_protect_opportunity_delete"
down_revision: Union[str, None] = "0053_script_scene_plan_gate"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("submissions_opportunity_id_fkey", "submissions", type_="foreignkey")
    op.create_foreign_key(
        "submissions_opportunity_id_fkey",
        "submissions",
        "opportunities",
        ["opportunity_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("submissions_opportunity_id_fkey", "submissions", type_="foreignkey")
    op.create_foreign_key(
        "submissions_opportunity_id_fkey",
        "submissions",
        "opportunities",
        ["opportunity_id"],
        ["id"],
        ondelete="CASCADE",
    )
