from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.db.models import ActorJournalEntry
from app.schemas.journal import ActorJournalEntryCreate, ActorJournalEntryUpdate


class JournalService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> list[ActorJournalEntry]:
        return list(
            self.db.scalars(
                select(ActorJournalEntry).order_by(ActorJournalEntry.date.desc(), ActorJournalEntry.created_at.desc())
            )
        )

    def create(self, payload: ActorJournalEntryCreate) -> ActorJournalEntry:
        entry = ActorJournalEntry(**payload.model_dump())
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def update(self, entry_id: UUID, payload: ActorJournalEntryUpdate) -> ActorJournalEntry:
        entry = self.db.get(ActorJournalEntry, entry_id)
        if not entry:
            raise NotFoundError("Journal entry not found")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(entry, key, value)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def delete(self, entry_id: UUID) -> None:
        entry = self.db.get(ActorJournalEntry, entry_id)
        if not entry:
            raise NotFoundError("Journal entry not found")
        self.db.delete(entry)
        self.db.commit()

    def record_once(
        self,
        *,
        event_type: str,
        title: str,
        description: str | None = None,
        entry_date: date | None = None,
        linked_breakdown_id=None,
        linked_audition_id=None,
        linked_material_id=None,
        linked_career_task_id=None,
        notes: str | None = None,
    ) -> ActorJournalEntry:
        entry_date = entry_date or date.today()
        statement = (
            select(ActorJournalEntry)
            .where(ActorJournalEntry.date == entry_date)
            .where(ActorJournalEntry.event_type == event_type)
            .where(ActorJournalEntry.title == title)
        )
        if linked_breakdown_id:
            statement = statement.where(ActorJournalEntry.linked_breakdown_id == linked_breakdown_id)
        if linked_audition_id:
            statement = statement.where(ActorJournalEntry.linked_audition_id == linked_audition_id)
        if linked_material_id:
            statement = statement.where(ActorJournalEntry.linked_material_id == linked_material_id)
        if linked_career_task_id:
            statement = statement.where(ActorJournalEntry.linked_career_task_id == linked_career_task_id)
        existing = self.db.scalar(statement)
        if existing:
            return existing
        entry = ActorJournalEntry(
            date=entry_date,
            event_type=event_type,
            title=title,
            description=description,
            linked_breakdown_id=linked_breakdown_id,
            linked_audition_id=linked_audition_id,
            linked_material_id=linked_material_id,
            linked_career_task_id=linked_career_task_id,
            notes=notes,
        )
        self.db.add(entry)
        return entry


def journal_date_from_datetime(value: datetime | date | None) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.utcnow().date()
