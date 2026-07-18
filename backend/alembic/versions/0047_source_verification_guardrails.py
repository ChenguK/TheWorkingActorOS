"""add source verification guardrail fields

Revision ID: 0047_source_verify
Revises: 0046_source_health
Create Date: 2026-07-04 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0047_source_verify"
down_revision = "0046_source_health"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("source_research_items", sa.Column("organization_name", sa.String(length=180), nullable=True))
    op.add_column("source_research_items", sa.Column("submitted_url", sa.String(length=1000), nullable=True))
    op.add_column("source_research_items", sa.Column("final_resolved_url", sa.String(length=1000), nullable=True))
    op.add_column("source_research_items", sa.Column("url_health_status", sa.String(length=80), nullable=False, server_default="Unchecked"))
    op.add_column("source_research_items", sa.Column("organization_legitimacy", sa.String(length=80), nullable=False, server_default="Unverified Organization"))
    op.add_column("source_research_items", sa.Column("source_usefulness", sa.String(length=80), nullable=False, server_default="Needs Review"))
    op.add_column("source_research_items", sa.Column("source_classification", sa.String(length=80), nullable=False, server_default="Needs Review"))
    op.add_column("source_research_items", sa.Column("verification_notes", sa.Text(), nullable=True))
    op.alter_column("source_research_items", "url_health_status", server_default=None)
    op.alter_column("source_research_items", "organization_legitimacy", server_default=None)
    op.alter_column("source_research_items", "source_usefulness", server_default=None)
    op.alter_column("source_research_items", "source_classification", server_default=None)


def downgrade() -> None:
    op.drop_column("source_research_items", "verification_notes")
    op.drop_column("source_research_items", "source_classification")
    op.drop_column("source_research_items", "source_usefulness")
    op.drop_column("source_research_items", "organization_legitimacy")
    op.drop_column("source_research_items", "url_health_status")
    op.drop_column("source_research_items", "final_resolved_url")
    op.drop_column("source_research_items", "submitted_url")
    op.drop_column("source_research_items", "organization_name")
