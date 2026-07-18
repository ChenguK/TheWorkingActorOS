from datetime import date as Date
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import TimestampedModel


class ActorJournalEntryCreate(BaseModel):
    date: Date
    event_type: str = "Manual"
    title: str
    description: str | None = None
    linked_breakdown_id: UUID | None = None
    linked_audition_id: UUID | None = None
    linked_material_id: UUID | None = None
    linked_career_task_id: UUID | None = None
    notes: str | None = None


class ActorJournalEntryUpdate(BaseModel):
    date: Date | None = None
    event_type: str | None = None
    title: str | None = None
    description: str | None = None
    linked_breakdown_id: UUID | None = None
    linked_audition_id: UUID | None = None
    linked_material_id: UUID | None = None
    linked_career_task_id: UUID | None = None
    notes: str | None = None


class ActorJournalEntryRead(TimestampedModel):
    date: Date
    event_type: str
    title: str
    description: str | None = None
    linked_breakdown_id: UUID | None = None
    linked_audition_id: UUID | None = None
    linked_material_id: UUID | None = None
    linked_career_task_id: UUID | None = None
    notes: str | None = None
