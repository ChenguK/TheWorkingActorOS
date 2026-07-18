"""facts inference split

Revision ID: 0032_facts_inference_split
Revises: 0031_role_fit_scores
Create Date: 2026-07-01 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0032_facts_inference_split"
down_revision: str | None = "0031_role_fit_scores"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "opportunities",
        sa.Column("extracted_facts", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.add_column(
        "opportunities",
        sa.Column("ai_inference", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.add_column(
        "breakdown_roles",
        sa.Column("extracted_facts", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.add_column(
        "breakdown_roles",
        sa.Column("ai_inference", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.alter_column("opportunities", "extracted_facts", server_default=None)
    op.alter_column("opportunities", "ai_inference", server_default=None)
    op.alter_column("breakdown_roles", "extracted_facts", server_default=None)
    op.alter_column("breakdown_roles", "ai_inference", server_default=None)


def downgrade() -> None:
    op.drop_column("breakdown_roles", "ai_inference")
    op.drop_column("breakdown_roles", "extracted_facts")
    op.drop_column("opportunities", "ai_inference")
    op.drop_column("opportunities", "extracted_facts")
