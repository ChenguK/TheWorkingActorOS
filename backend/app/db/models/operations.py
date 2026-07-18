from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AuditionCalendarEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "audition_calendar_events"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    opportunity_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True
    )
    submission_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("submissions.id", ondelete="SET NULL"), nullable=True
    )
    start_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_virtual: Mapped[bool] = mapped_column(default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    opportunity = relationship("Opportunity")
    submission = relationship("Submission")

    __table_args__ = (
        CheckConstraint(
            "event_type IN ('Submission Due', 'Self-Tape Due', 'Virtual Callback', "
            "'In-Person Callback', 'Fitting', 'Shoot', 'Meeting', 'Other')",
            name="ck_audition_calendar_events_type",
        ),
    )


class AvailabilityBlock(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "availability_blocks"

    actor_profile_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("actor_profiles.id", ondelete="CASCADE"), nullable=True, index=True
    )
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    block_type: Mapped[str] = mapped_column(String(80), nullable=False, default="Personal Commitment")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    actor_profile = relationship("ActorProfile")

    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="ck_availability_blocks_date_order"),
    )


class ProfessionalEquipmentProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "professional_equipment_profiles"

    actor_profile_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("actor_profiles.id", ondelete="CASCADE"), nullable=True, index=True
    )
    cameras: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    lighting: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    audio_equipment: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    backdrops: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    editing_software: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    teleprompter: Mapped[bool] = mapped_column(default=False, nullable=False)
    reader_availability: Mapped[str | None] = mapped_column(String(255), nullable=True)
    internet_upload_speed: Mapped[str | None] = mapped_column(String(120), nullable=True)
    home_audition_space: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    actor_profile = relationship("ActorProfile")


class CastingPlatformSubscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "casting_platform_subscriptions"

    platform_name: Mapped[str] = mapped_column(String(120), nullable=False)
    has_subscription: Mapped[bool] = mapped_column(default=False, nullable=False)
    subscription_level: Mapped[str | None] = mapped_column(String(120), nullable=True)
    monthly_cost: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    annual_cost: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    renewal_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)

    check_ins = relationship(
        "DailyPlatformCheckIn",
        back_populates="platform_subscription",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("platform_name", name="uq_casting_platform_subscriptions_platform_name"),
    )


class DailyPlatformCheckIn(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "daily_platform_check_ins"

    platform_subscription_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("casting_platform_subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    check_date: Mapped[date] = mapped_column(Date, nullable=False)
    timezone: Mapped[str] = mapped_column(String(80), nullable=False, default="America/New_York")
    checked_today: Mapped[bool] = mapped_column(default=False, nullable=False)
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    platform_subscription = relationship("CastingPlatformSubscription", back_populates="check_ins")

    __table_args__ = (
        UniqueConstraint(
            "platform_subscription_id",
            "check_date",
            "timezone",
            name="uq_daily_platform_check_ins_platform_date_timezone",
        ),
    )
