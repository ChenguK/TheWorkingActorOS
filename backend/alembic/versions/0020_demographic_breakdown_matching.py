"""demographic breakdown matching

Revision ID: 0020_demographics
Revises: 0019_supervised_breakdowns
Create Date: 2026-06-25 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0020_demographics"
down_revision: str | None = "0019_supervised_breakdowns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "actor_profiles",
        sa.Column("gender_identities", postgresql.ARRAY(sa.String()), server_default=sa.text("'{}'"), nullable=False),
    )
    op.add_column("actor_profiles", sa.Column("gender_expression", sa.String(length=160), nullable=True))
    op.add_column("actor_profiles", sa.Column("pronouns", sa.String(length=120), nullable=True))
    op.add_column(
        "actor_profiles",
        sa.Column("ethnicities", postgresql.ARRAY(sa.String()), server_default=sa.text("'{}'"), nullable=False),
    )
    op.add_column(
        "actor_profiles",
        sa.Column("racial_identities", postgresql.ARRAY(sa.String()), server_default=sa.text("'{}'"), nullable=False),
    )
    op.add_column(
        "actor_profiles",
        sa.Column("nationalities", postgresql.ARRAY(sa.String()), server_default=sa.text("'{}'"), nullable=False),
    )
    op.add_column(
        "actor_profiles",
        sa.Column("languages", postgresql.ARRAY(sa.String()), server_default=sa.text("'{}'"), nullable=False),
    )
    op.add_column(
        "actor_profiles",
        sa.Column("accents", postgresql.ARRAY(sa.String()), server_default=sa.text("'{}'"), nullable=False),
    )
    op.add_column(
        "actor_profiles",
        sa.Column("disability_identities", postgresql.ARRAY(sa.String()), server_default=sa.text("'{}'"), nullable=False),
    )
    op.add_column("actor_profiles", sa.Column("accessibility_notes", sa.Text(), nullable=True))
    op.add_column("actor_profiles", sa.Column("demographic_notes", sa.Text(), nullable=True))

    op.add_column(
        "opportunities",
        sa.Column("demographic_match_status", sa.String(length=40), server_default="Needs Review", nullable=False),
    )
    op.add_column("opportunities", sa.Column("demographic_match_explanation", sa.Text(), nullable=True))
    op.add_column(
        "opportunities",
        sa.Column(
            "demographic_match_details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_opportunities_demographic_match_status",
        "opportunities",
        "demographic_match_status IN ('Match', 'Needs Review', 'Not a Match')",
    )

    for column in (
        "gender_identities",
        "ethnicities",
        "racial_identities",
        "nationalities",
        "languages",
        "accents",
        "disability_identities",
    ):
        op.alter_column("actor_profiles", column, server_default=None)
    op.alter_column("opportunities", "demographic_match_status", server_default=None)
    op.alter_column("opportunities", "demographic_match_details", server_default=None)


def downgrade() -> None:
    op.drop_constraint("ck_opportunities_demographic_match_status", "opportunities", type_="check")
    op.drop_column("opportunities", "demographic_match_details")
    op.drop_column("opportunities", "demographic_match_explanation")
    op.drop_column("opportunities", "demographic_match_status")

    op.drop_column("actor_profiles", "demographic_notes")
    op.drop_column("actor_profiles", "accessibility_notes")
    op.drop_column("actor_profiles", "disability_identities")
    op.drop_column("actor_profiles", "accents")
    op.drop_column("actor_profiles", "languages")
    op.drop_column("actor_profiles", "nationalities")
    op.drop_column("actor_profiles", "racial_identities")
    op.drop_column("actor_profiles", "ethnicities")
    op.drop_column("actor_profiles", "pronouns")
    op.drop_column("actor_profiles", "gender_expression")
    op.drop_column("actor_profiles", "gender_identities")
