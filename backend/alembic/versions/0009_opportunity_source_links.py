"""opportunity source links

Revision ID: 0009_links
Revises: 0008_swot
Create Date: 2026-06-23 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0009_links"
down_revision: Union[str, None] = "0008_swot"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("opportunities", sa.Column("original_post_url", sa.String(length=1000), nullable=True))


def downgrade() -> None:
    op.drop_column("opportunities", "original_post_url")
