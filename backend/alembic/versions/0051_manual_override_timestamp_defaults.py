"""add timestamp defaults to manual override logs

Revision ID: 0051_manual_override_timestamps
Revises: 0050_script_scene_finder
Create Date: 2026-07-06 00:00:00.000000
"""

from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "0051_manual_override_timestamps"
down_revision: Union[str, None] = "0050_script_scene_finder"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.alter_column(
        "manual_override_logs",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        existing_nullable=False,
    )
    op.alter_column(
        "manual_override_logs",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "manual_override_logs",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=None,
        existing_nullable=False,
    )
    op.alter_column(
        "manual_override_logs",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=None,
        existing_nullable=False,
    )
