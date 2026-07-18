from sqlalchemy import CheckConstraint, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class TravelPreference(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "travel_preferences"

    actor_profile_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("actor_profiles.id", ondelete="CASCADE"), nullable=False
    )
    max_local_drive_time: Mapped[int] = mapped_column(nullable=False, default=300)
    extended_drive_time: Mapped[int] = mapped_column(nullable=False, default=720)
    flight_allowed: Mapped[bool] = mapped_column(nullable=False, default=True)
    housing_required: Mapped[bool] = mapped_column(nullable=False, default=False)
    international_allowed: Mapped[bool] = mapped_column(nullable=False, default=False)
    audition_max_drive_time: Mapped[int] = mapped_column(nullable=False, default=120)
    audition_virtual_allowed: Mapped[bool] = mapped_column(nullable=False, default=True)
    audition_self_tape_allowed: Mapped[bool] = mapped_column(nullable=False, default=True)
    working_as_local_drive_time: Mapped[int] = mapped_column(nullable=False, default=300)
    working_as_local_housing_self_provided: Mapped[bool] = mapped_column(nullable=False, default=True)
    require_travel_housing_over_local_drive: Mapped[bool] = mapped_column(nullable=False, default=True)
    audition_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    working_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    actor_profile = relationship("ActorProfile", back_populates="travel_preferences")

    __table_args__ = (
        CheckConstraint("max_local_drive_time > 0", name="ck_travel_max_drive_positive"),
        CheckConstraint(
            "extended_drive_time >= max_local_drive_time", name="ck_travel_extended_gte_local"
        ),
        CheckConstraint("audition_max_drive_time > 0", name="ck_travel_audition_max_drive_positive"),
        CheckConstraint("working_as_local_drive_time > 0", name="ck_travel_working_as_local_drive_positive"),
    )
