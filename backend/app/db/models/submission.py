from datetime import datetime

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Numeric, String, Table, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


SubmissionAsset = Table(
    "submission_assets",
    Base.metadata,
    Column(
        "submission_id",
        UUID(as_uuid=True),
        ForeignKey("submissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "asset_id",
        UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="RESTRICT"),
        primary_key=True,
    ),
)


class Submission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "submissions"

    actor_profile_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("actor_profiles.id", ondelete="CASCADE"), nullable=False
    )
    opportunity_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False
    )
    current_status: Mapped[str] = mapped_column(String(80), nullable=False, default="Submitted")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submission_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    media_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    travel_cost: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    housing_cost: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    parking_cost: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    other_cost: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    total_cost: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)

    actor_profile = relationship("ActorProfile", back_populates="submissions")
    opportunity = relationship("Opportunity", back_populates="submissions")
    assets = relationship("Asset", secondary=SubmissionAsset)
    status_history = relationship(
        "SubmissionStatusHistory",
        back_populates="submission",
        cascade="all, delete-orphan",
        order_by="SubmissionStatusHistory.occurred_at",
    )

    __table_args__ = (
        CheckConstraint(
            "current_status IN ('Submitted', 'Requested', 'Self-Tape Callback', "
            "'In-Person Callback', 'Pinned', 'Booked', 'Passed', 'No Response')",
            name="ck_submissions_current_status",
        ),
    )


class SubmissionStatusHistory(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "submission_status_history"

    submission_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(80), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    submission = relationship("Submission", back_populates="status_history")

    __table_args__ = (
        CheckConstraint(
            "status IN ('Submitted', 'Requested', 'Self-Tape Callback', 'In-Person Callback', "
            "'Pinned', 'Booked', 'Passed', 'No Response')",
            name="ck_submission_status_history_status",
        ),
    )
