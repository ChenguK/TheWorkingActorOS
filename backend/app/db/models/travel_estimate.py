from datetime import datetime

from sqlalchemy import DateTime, Float, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class TravelEstimate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "travel_estimates"

    origin_text: Mapped[str] = mapped_column(String(500), nullable=False)
    destination_text: Mapped[str] = mapped_column(String(500), nullable=False)
    origin_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    origin_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    destination_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    destination_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    drive_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    drive_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_miles: Mapped[float | None] = mapped_column(Float, nullable=True)
    provider: Mapped[str] = mapped_column(String(80), nullable=False, default="manual")
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_manual_override: Mapped[bool] = mapped_column(default=False, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


Index("ix_travel_estimates_origin_destination", TravelEstimate.origin_text, TravelEstimate.destination_text)
