"""chief of staff visibility states

Revision ID: 0036_chief_staff_visibility
Revises: 0035_executive_intelligence
Create Date: 2026-07-02 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0036_chief_staff_visibility"
down_revision: Union[str, None] = "0035_executive_intelligence"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_opportunities_visibility_status", "opportunities", type_="check")
    op.create_check_constraint(
        "ck_opportunities_visibility_status",
        "opportunities",
        "visibility_status IN ('visible', 'hidden', 'discarded', 'travel_exception')",
    )
    op.execute(
        "UPDATE opportunities SET visibility_status = 'travel_exception', hidden_by_rule = 'travel_exception' "
        "WHERE visibility_status = 'hidden' AND hidden_by_rule IN "
        "('dealbreaker_audition_travel', 'in_person_audition_drive_time')"
    )
    op.execute(
        "UPDATE opportunities SET visibility_status = 'discarded' "
        "WHERE visibility_status = 'hidden' AND hidden_by_rule IN "
        "('dealbreaker_role_type', 'dealbreaker_demographic_mismatch', 'dealbreaker_eligibility', "
        "'breakdown_classification_rejected', 'user_rejected')"
    )
    op.create_table(
        "chief_of_staff_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("actor_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_dashboard_visit_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_profile_id"], ["actor_profiles.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_chief_of_staff_states_actor_profile_id", "chief_of_staff_states", ["actor_profile_id"])


def downgrade() -> None:
    op.drop_table("chief_of_staff_states")
    op.execute(
        "UPDATE opportunities SET visibility_status = 'hidden' "
        "WHERE visibility_status IN ('discarded', 'travel_exception')"
    )
    op.drop_constraint("ck_opportunities_visibility_status", "opportunities", type_="check")
    op.create_check_constraint(
        "ck_opportunities_visibility_status",
        "opportunities",
        "visibility_status IN ('visible', 'hidden')",
    )
