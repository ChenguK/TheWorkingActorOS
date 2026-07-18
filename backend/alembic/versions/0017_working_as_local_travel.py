"""working as local travel

Revision ID: 0017_work_local
Revises: 0016_split_travel
Create Date: 2026-06-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_work_local"
down_revision: str | None = "0016_split_travel"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "travel_preferences",
        sa.Column("working_as_local_drive_time", sa.Integer(), server_default=sa.text("300"), nullable=False),
    )
    op.execute("UPDATE travel_preferences SET working_as_local_drive_time = max_local_drive_time")
    op.add_column(
        "travel_preferences",
        sa.Column("working_as_local_housing_self_provided", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.add_column(
        "travel_preferences",
        sa.Column("require_travel_housing_over_local_drive", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.create_check_constraint(
        "ck_travel_working_as_local_drive_positive",
        "travel_preferences",
        "working_as_local_drive_time > 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_travel_working_as_local_drive_positive", "travel_preferences", type_="check")
    op.drop_column("travel_preferences", "require_travel_housing_over_local_drive")
    op.drop_column("travel_preferences", "working_as_local_housing_self_provided")
    op.drop_column("travel_preferences", "working_as_local_drive_time")
