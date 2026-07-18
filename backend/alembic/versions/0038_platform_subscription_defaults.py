"""keep blank platform subscriptions inactive until configured

Revision ID: 0038_platform_defaults
Revises: 0037_platform_checkins
Create Date: 2026-07-03 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0038_platform_defaults"
down_revision: Union[str, None] = "0037_platform_checkins"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE casting_platform_subscriptions
        SET has_subscription = false
        WHERE COALESCE(TRIM(subscription_level), '') = ''
          AND monthly_cost IS NULL
          AND annual_cost IS NULL
          AND renewal_date IS NULL
          AND COALESCE(TRIM(notes), '') = ''
        """
    )


def downgrade() -> None:
    pass
