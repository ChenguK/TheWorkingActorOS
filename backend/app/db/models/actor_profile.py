from sqlalchemy import CheckConstraint, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ActorProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "actor_profiles"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sag_status: Mapped[str] = mapped_column(String(100), nullable=False)
    union_status: Mapped[str] = mapped_column(String(100), nullable=False)
    current_location: Mapped[str] = mapped_column(String(255), nullable=False)
    playable_age_min: Mapped[int] = mapped_column(nullable=False)
    playable_age_max: Mapped[int] = mapped_column(nullable=False)
    secondary_playable_age_min: Mapped[int | None] = mapped_column(nullable=True)
    secondary_playable_age_max: Mapped[int | None] = mapped_column(nullable=True)
    skills: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    gender_identities: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    gender_expression: Mapped[str | None] = mapped_column(String(160), nullable=True)
    pronouns: Mapped[str | None] = mapped_column(String(120), nullable=True)
    ethnicities: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    racial_identities: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    nationalities: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    languages: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    accents: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    disability_identities: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    included_role_types: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    excluded_role_types: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    accessibility_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    demographic_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    travel_preferences = relationship(
        "TravelPreference", back_populates="actor_profile", cascade="all, delete-orphan"
    )
    assets = relationship("Asset", back_populates="actor_profile", cascade="all, delete-orphan")
    submissions = relationship(
        "Submission", back_populates="actor_profile", cascade="all, delete-orphan"
    )
    representations = relationship(
        "Representation", back_populates="actor_profile", cascade="all, delete-orphan"
    )
    acting_credits = relationship(
        "ActingCredit", back_populates="actor_profile", cascade="all, delete-orphan"
    )
    dashboard_widgets = relationship(
        "DashboardWidget", back_populates="actor_profile", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("playable_age_min <= playable_age_max", name="ck_actor_primary_age_range"),
        CheckConstraint(
            "secondary_playable_age_min IS NULL OR secondary_playable_age_max IS NULL "
            "OR secondary_playable_age_min <= secondary_playable_age_max",
            name="ck_actor_secondary_age_range",
        ),
    )
