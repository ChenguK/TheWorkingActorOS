"""role preferences and rejection text

Revision ID: 0034_role_prefs
Revises: 0033_discovery_limits
Create Date: 2026-07-01 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0034_role_prefs"
down_revision: Union[str, None] = "0033_discovery_limits"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEFAULT_INCLUDED = [
    "Lead",
    "Supporting",
    "Principal",
    "Guest Star",
    "Co-Star",
    "Recurring",
    "Series Regular",
    "Voiceover",
    "Commercial Principal",
    "Theater Principal",
]

DEFAULT_EXCLUDED = [
    "Background",
    "Extra",
    "Ensemble",
    "Brand Ambassador",
    "Class",
    "Workshop",
    "Seminar",
    "Crew",
    "Staff Job",
    "Internship",
    "Administrative Job",
]


def upgrade() -> None:
    op.add_column(
        "actor_profiles",
        sa.Column(
            "included_role_types",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default=sa.text("ARRAY[]::varchar[]"),
        ),
    )
    op.add_column(
        "actor_profiles",
        sa.Column(
            "excluded_role_types",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default=sa.text("ARRAY[]::varchar[]"),
        ),
    )
    op.add_column("opportunities", sa.Column("highlighted_text_as_rejection_reason", sa.Text(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE actor_profiles SET included_role_types = :included, excluded_role_types = :excluded"
        ).bindparams(
            sa.bindparam("included", value=DEFAULT_INCLUDED, type_=postgresql.ARRAY(sa.String())),
            sa.bindparam("excluded", value=DEFAULT_EXCLUDED, type_=postgresql.ARRAY(sa.String())),
        )
    )
    op.alter_column("actor_profiles", "included_role_types", server_default=None)
    op.alter_column("actor_profiles", "excluded_role_types", server_default=None)


def downgrade() -> None:
    op.drop_column("opportunities", "highlighted_text_as_rejection_reason")
    op.drop_column("actor_profiles", "excluded_role_types")
    op.drop_column("actor_profiles", "included_role_types")
