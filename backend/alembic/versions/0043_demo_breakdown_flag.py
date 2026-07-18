"""add demo data flag to breakdowns

Revision ID: 0043_demo_breakdown_flag
Revises: 0042_recommend_feedback
Create Date: 2026-07-03 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0043_demo_breakdown_flag"
down_revision = "0042_recommend_feedback"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("opportunities", sa.Column("is_demo_data", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index("ix_opportunities_is_demo_data", "opportunities", ["is_demo_data"])
    op.execute(
        """
        UPDATE opportunities
        SET
            is_demo_data = TRUE,
            visibility_status = CASE
                WHEN visibility_status = 'discarded' THEN visibility_status
                ELSE 'discarded'
            END,
            hidden_by_rule = COALESCE(hidden_by_rule, 'demo_data'),
            hidden_reason = COALESCE(hidden_reason, 'Demo/sample breakdown hidden from actor workflows.'),
            rejection_reason = COALESCE(rejection_reason, 'Demo/sample breakdown hidden from actor workflows.'),
            status = CASE
                WHEN status = 'archived' THEN status
                ELSE 'archived'
            END
        WHERE
            COALESCE(original_post_url, '') ILIKE '%example.com%'
            OR project ILIKE '% demo'
            OR project ILIKE '% demo %'
            OR project ILIKE '%Feature Demo%'
            OR project ILIKE '%Procedural Demo%'
            OR description ILIKE '%feature demo%'
            OR description ILIKE '%procedural demo%'
        """
    )
    op.alter_column("opportunities", "is_demo_data", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_opportunities_is_demo_data", table_name="opportunities")
    op.drop_column("opportunities", "is_demo_data")
