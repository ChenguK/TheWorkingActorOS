"""role fit scores

Revision ID: 0031_role_fit_scores
Revises: 0030_breakdown_intel
Create Date: 2026-07-01 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0031_role_fit_scores"
down_revision: str | None = "0030_breakdown_intel"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("breakdown_roles", sa.Column("role_type", sa.String(length=120), nullable=True))
    op.add_column("breakdown_roles", sa.Column("billing", sa.String(length=120), nullable=True))
    op.add_column("breakdown_roles", sa.Column("preparation_notes", sa.Text(), nullable=True))
    op.add_column("breakdown_roles", sa.Column("fit_score", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("breakdown_roles", sa.Column("confidence_score", sa.Integer(), nullable=False, server_default="50"))
    op.create_check_constraint(
        "ck_breakdown_roles_fit_score",
        "breakdown_roles",
        "fit_score >= 0 AND fit_score <= 100",
    )
    op.create_check_constraint(
        "ck_breakdown_roles_confidence_score",
        "breakdown_roles",
        "confidence_score >= 0 AND confidence_score <= 100",
    )
    op.alter_column("breakdown_roles", "fit_score", server_default=None)
    op.alter_column("breakdown_roles", "confidence_score", server_default=None)


def downgrade() -> None:
    op.drop_constraint("ck_breakdown_roles_confidence_score", "breakdown_roles", type_="check")
    op.drop_constraint("ck_breakdown_roles_fit_score", "breakdown_roles", type_="check")
    op.drop_column("breakdown_roles", "confidence_score")
    op.drop_column("breakdown_roles", "fit_score")
    op.drop_column("breakdown_roles", "preparation_notes")
    op.drop_column("breakdown_roles", "billing")
    op.drop_column("breakdown_roles", "role_type")
