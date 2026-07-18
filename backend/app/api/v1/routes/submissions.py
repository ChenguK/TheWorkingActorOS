from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.submission import (
    SubmissionCreate,
    SubmissionRead,
    SubmissionStatusHistoryCreate,
    SubmissionUpdate,
)
from app.services.submission_service import SubmissionService

router = APIRouter()


@router.get("", response_model=list[SubmissionRead])
def list_submissions(db: Session = Depends(get_db)):
    return SubmissionService(db).list()


@router.get("/waiting", response_model=list[SubmissionRead])
def list_waiting_submissions(db: Session = Depends(get_db)):
    return SubmissionService(db).waiting()


@router.post("", response_model=SubmissionRead, status_code=201)
def create_submission(payload: SubmissionCreate, db: Session = Depends(get_db)):
    try:
        return SubmissionService(db).create(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{submission_id}", response_model=SubmissionRead)
def get_submission(submission_id: UUID, db: Session = Depends(get_db)):
    return SubmissionService(db).get(submission_id)


@router.patch("/{submission_id}", response_model=SubmissionRead)
def update_submission(submission_id: UUID, payload: SubmissionUpdate, db: Session = Depends(get_db)):
    return SubmissionService(db).update(submission_id, payload)


@router.post("/{submission_id}/status-history", response_model=SubmissionRead)
def add_submission_status(
    submission_id: UUID, payload: SubmissionStatusHistoryCreate, db: Session = Depends(get_db)
):
    try:
        return SubmissionService(db).add_status(submission_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/{submission_id}", status_code=204)
def delete_submission(submission_id: UUID, db: Session = Depends(get_db)):
    SubmissionService(db).delete(submission_id)
