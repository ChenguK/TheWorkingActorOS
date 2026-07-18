from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DashboardWidget(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "dashboard_widgets"
    __table_args__ = (
        CheckConstraint("size IN ('small', 'medium', 'large')", name="ck_dashboard_widgets_size"),
        UniqueConstraint("actor_profile_id", "widget_id", name="uq_dashboard_widgets_actor_widget"),
    )

    actor_profile_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("actor_profiles.id", ondelete="CASCADE"), nullable=True, index=True
    )
    widget_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(180), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"), index=True)
    size: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'medium'"))

    actor_profile = relationship("ActorProfile", back_populates="dashboard_widgets")


class FocusModePreference(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "focus_mode_preferences"
    __table_args__ = (
        CheckConstraint(
            "active_mode IN ('Audition Mode', 'Career Building Mode', 'Casting Goals Mode', 'Relationship Mode', 'Analytics Mode')",
            name="ck_focus_mode_preferences_active_mode",
        ),
        UniqueConstraint("actor_profile_id", name="uq_focus_mode_preferences_actor"),
    )

    actor_profile_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("actor_profiles.id", ondelete="CASCADE"), nullable=True, index=True
    )
    active_mode: Mapped[str] = mapped_column(String(80), nullable=False, server_default=text("'Audition Mode'"))

    actor_profile = relationship("ActorProfile")
