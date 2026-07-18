from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ActorJournalEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "actor_journal_entries"

    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    linked_breakdown_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True, index=True
    )
    linked_audition_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("submissions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    linked_material_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    linked_career_task_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("career_development_tasks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    breakdown = relationship("Opportunity")
    audition = relationship("Submission")
    material = relationship("Asset")
    career_task = relationship("CareerDevelopmentTask")
