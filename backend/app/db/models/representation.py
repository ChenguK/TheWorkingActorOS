from datetime import date

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Representation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "representations"

    actor_profile_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("actor_profiles.id", ondelete="CASCADE"), nullable=False
    )
    agency_name: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    agent_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    agent_phone: Mapped[str | None] = mapped_column(String(80), nullable=True)
    agency_website: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    representation_type: Mapped[str] = mapped_column(String(80), nullable=False)
    market: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    actor_profile = relationship("ActorProfile", back_populates="representations")

    __table_args__ = (
        CheckConstraint(
            "representation_type IN ('Theatrical', 'Commercial', 'Voiceover', 'Print', 'Manager', 'Other')",
            name="ck_representations_type",
        ),
    )


class ActingCredit(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "acting_credits"

    actor_profile_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("actor_profiles.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    section_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    section_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    highlighted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    project_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role_or_character: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    production_company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    network_or_distributor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    director: Mapped[str | None] = mapped_column(String(255), nullable=True)
    episode_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    season_episode: Mapped[str | None] = mapped_column(String(80), nullable=True)
    year: Mapped[str | None] = mapped_column(String(20), nullable=True)
    union_status: Mapped[str | None] = mapped_column(String(80), nullable=True)

    class_or_program: Mapped[str | None] = mapped_column(String(255), nullable=True)
    instructor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    institution: Mapped[str | None] = mapped_column(String(255), nullable=True)

    skill_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    skill_category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    proficiency: Mapped[str | None] = mapped_column(String(80), nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    actor_profile = relationship("ActorProfile", back_populates="acting_credits")

    __table_args__ = (
        CheckConstraint(
            "category IN ('Television', 'Film', 'Commercial', 'Theater', 'New Media', "
            "'Voiceover', 'Industrial', 'Print', 'Training', 'Special Skills', 'Other')",
            name="ck_acting_credits_category",
        ),
    )
