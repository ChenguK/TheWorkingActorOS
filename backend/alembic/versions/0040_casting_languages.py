"""casting language parser records

Revision ID: 0040_casting_languages
Revises: 0039_character_profiles
Create Date: 2026-07-03 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0040_casting_languages"
down_revision: Union[str, None] = "0039_character_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def uuid_pk() -> sa.Column:
    return sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True)


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "casting_languages",
        uuid_pk(),
        sa.Column("breakdown_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("breakdown_role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("billing", sa.String(120), nullable=True),
        sa.Column("age_range", sa.String(80), nullable=True),
        sa.Column("gender", sa.String(160), nullable=True),
        sa.Column("ethnicity", sa.String(255), nullable=True),
        sa.Column("union", sa.String(120), nullable=True),
        sa.Column("compensation", sa.String(255), nullable=True),
        sa.Column("special_notes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        *timestamps(),
        sa.ForeignKeyConstraint(["breakdown_id"], ["opportunities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["breakdown_role_id"], ["breakdown_roles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("breakdown_role_id", name="uq_casting_languages_breakdown_role_id"),
    )
    op.create_index("ix_casting_languages_breakdown_id", "casting_languages", ["breakdown_id"])
    op.create_index("ix_casting_languages_breakdown_role_id", "casting_languages", ["breakdown_role_id"])


def downgrade() -> None:
    op.drop_index("ix_casting_languages_breakdown_role_id", table_name="casting_languages")
    op.drop_index("ix_casting_languages_breakdown_id", table_name="casting_languages")
    op.drop_table("casting_languages")
