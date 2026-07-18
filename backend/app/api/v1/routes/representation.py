from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.representation import (
    ActingCreditCreate,
    ActingCreditRead,
    ActingCreditUpdate,
    RepresentationCreate,
    RepresentationRead,
    RepresentationUpdate,
)
from app.services.representation_service import RepresentationService

router = APIRouter()


@router.get("", response_model=list[RepresentationRead])
def list_representations(actor_profile_id: UUID | None = None, db: Session = Depends(get_db)):
    return RepresentationService(db).list_representations(actor_profile_id)


@router.post("", response_model=RepresentationRead, status_code=201)
def create_representation(payload: RepresentationCreate, db: Session = Depends(get_db)):
    return RepresentationService(db).create_representation(payload)


@router.get("/acting-credits/list", response_model=list[ActingCreditRead])
def list_acting_credits(actor_profile_id: UUID | None = None, db: Session = Depends(get_db)):
    return RepresentationService(db).list_credits(actor_profile_id)


@router.get("/acting-credits/resume-pdf/{actor_profile_id}")
def download_generated_resume(actor_profile_id: UUID, db: Session = Depends(get_db)):
    asset = RepresentationService(db).get_or_create_generated_resume(actor_profile_id, "pdf")
    return FileResponse(
        asset.local_file_path,
        media_type=asset.mime_type or "application/pdf",
        filename=asset.original_filename or "acting-resume.pdf",
    )


@router.get("/acting-credits/resume-docx/{actor_profile_id}")
def download_generated_resume_docx(actor_profile_id: UUID, db: Session = Depends(get_db)):
    asset = RepresentationService(db).get_or_create_generated_resume(actor_profile_id, "docx")
    return FileResponse(
        asset.local_file_path,
        media_type=asset.mime_type
        or "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=asset.original_filename or "acting-resume.docx",
    )


@router.post("/acting-credits", response_model=ActingCreditRead, status_code=201)
def create_acting_credit(payload: ActingCreditCreate, db: Session = Depends(get_db)):
    return RepresentationService(db).create_credit(payload)


@router.patch("/acting-credits/{credit_id}", response_model=ActingCreditRead)
def update_acting_credit(
    credit_id: UUID,
    payload: ActingCreditUpdate,
    db: Session = Depends(get_db),
):
    return RepresentationService(db).update_credit(credit_id, payload)


@router.delete("/acting-credits/{credit_id}", status_code=204)
def delete_acting_credit(credit_id: UUID, db: Session = Depends(get_db)):
    RepresentationService(db).delete_credit(credit_id)
    return None


@router.patch("/{representation_id}", response_model=RepresentationRead)
def update_representation(
    representation_id: UUID,
    payload: RepresentationUpdate,
    db: Session = Depends(get_db),
):
    return RepresentationService(db).update_representation(representation_id, payload)


@router.delete("/{representation_id}", status_code=204)
def delete_representation(representation_id: UUID, db: Session = Depends(get_db)):
    RepresentationService(db).delete_representation(representation_id)
    return None
