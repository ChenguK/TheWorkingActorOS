from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class SourceExclusion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "source_exclusions"

    source_name: Mapped[str] = mapped_column(String(160), nullable=False)
    external_source_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    canonical_url_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content_version_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    exclusion_type: Mapped[str] = mapped_column(String(40), nullable=False)
    classification: Mapped[str] = mapped_column(String(80), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(80), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    times_seen: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "external_source_id IS NOT NULL OR canonical_url_hash IS NOT NULL",
            name="ck_source_exclusions_identity",
        ),
        CheckConstraint(
            "external_source_id IS NOT NULL OR expires_at IS NOT NULL",
            name="ck_source_exclusions_weak_expiry",
        ),
        CheckConstraint("times_seen >= 1", name="ck_source_exclusions_times_seen"),
        CheckConstraint("last_seen_at >= first_seen_at", name="ck_source_exclusions_seen_order"),
        CheckConstraint(
            "expires_at IS NULL OR expires_at > first_seen_at",
            name="ck_source_exclusions_expiry_order",
        ),
        CheckConstraint(
            "exclusion_type IN ('confirmed_non_acting')", name="ck_source_exclusions_type"
        ),
        CheckConstraint(
            "classification IN ('Crew Job', 'Non-Acting Job')",
            name="ck_source_exclusions_classification",
        ),
        CheckConstraint(
            "reason_code IN ('provider_listing_rule', 'deterministic_classification')",
            name="ck_source_exclusions_reason",
        ),
        Index(
            "uq_source_exclusions_source_external_id",
            "source_name",
            "external_source_id",
            unique=True,
            postgresql_where=text("external_source_id IS NOT NULL"),
        ),
        Index(
            "uq_source_exclusions_source_url_hash",
            "source_name",
            "canonical_url_hash",
            unique=True,
            postgresql_where=text("canonical_url_hash IS NOT NULL"),
        ),
    )

