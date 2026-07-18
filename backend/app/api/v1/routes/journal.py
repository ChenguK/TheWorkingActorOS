from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.journal import (
    ActorJournalEntryCreate,
    ActorJournalEntryRead,
    ActorJournalEntryUpdate,
)
from app.services.journal_service import JournalService

router = APIRouter()


@router.get("", response_model=list[ActorJournalEntryRead])
def list_journal_entries(db: Session = Depends(get_db)):
    return JournalService(db).list()


@router.post("", response_model=ActorJournalEntryRead, status_code=201)
def create_journal_entry(payload: ActorJournalEntryCreate, db: Session = Depends(get_db)):
    return JournalService(db).create(payload)


@router.patch("/{entry_id}", response_model=ActorJournalEntryRead)
def update_journal_entry(entry_id: UUID, payload: ActorJournalEntryUpdate, db: Session = Depends(get_db)):
    return JournalService(db).update(entry_id, payload)


@router.delete("/{entry_id}", status_code=204)
def delete_journal_entry(entry_id: UUID, db: Session = Depends(get_db)):
    JournalService(db).delete(entry_id)
