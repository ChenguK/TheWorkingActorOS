"""split travel preferences

Revision ID: 0016_split_travel
Revises: 0015_dashboard
Create Date: 2026-06-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_split_travel"
down_revision: str | None = "0015_dashboard"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "travel_preferences",
        sa.Column("audition_max_drive_time", sa.Integer(), server_default=sa.text("120"), nullable=False),
    )
    op.add_column(
        "travel_preferences",
        sa.Column("audition_virtual_allowed", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.add_column(
        "travel_preferences",
        sa.Column("audition_self_tape_allowed", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.add_column("travel_preferences", sa.Column("audition_notes", sa.Text(), nullable=True))
    op.add_column("travel_preferences", sa.Column("working_notes", sa.Text(), nullable=True))
    op.create_check_constraint(
        "ck_travel_audition_max_drive_positive",
        "travel_preferences",
        "audition_max_drive_time > 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_travel_audition_max_drive_positive", "travel_preferences", type_="check")
    op.drop_column("travel_preferences", "working_notes")
    op.drop_column("travel_preferences", "audition_notes")
    op.drop_column("travel_preferences", "audition_self_tape_allowed")
    op.drop_column("travel_preferences", "audition_virtual_allowed")
    op.drop_column("travel_preferences", "audition_max_drive_time")
