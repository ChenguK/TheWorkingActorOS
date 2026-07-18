"""archetype confidence scores

Revision ID: 0041_archetype_scores
Revises: 0040_casting_languages
Create Date: 2026-07-03 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0041_archetype_scores"
down_revision: Union[str, None] = "0040_casting_languages"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "character_profiles",
        sa.Column("archetype_confidence_scores", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("character_profiles", "archetype_confidence_scores")
