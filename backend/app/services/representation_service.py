from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.db.models import ActingCredit, ActorProfile, Representation
from app.schemas.representation import (
    ActingCreditCreate,
    ActingCreditUpdate,
    RepresentationCreate,
    RepresentationUpdate,
)
from app.services.resume_pdf_service import ResumePdfService


class RepresentationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_representations(self, actor_profile_id: UUID | None = None) -> list[Representation]:
        statement = select(Representation).order_by(Representation.active.desc(), Representation.agency_name.asc())
        if actor_profile_id:
            statement = statement.where(Representation.actor_profile_id == actor_profile_id)
        return list(self.db.scalars(statement))

    def create_representation(self, payload: RepresentationCreate) -> Representation:
        self._actor_or_404(payload.actor_profile_id)
        record = Representation(**payload.model_dump())
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def update_representation(self, representation_id: UUID, payload: RepresentationUpdate) -> Representation:
        record = self._representation_or_404(representation_id)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(record, key, value)
        self.db.commit()
        self.db.refresh(record)
        return record

    def delete_representation(self, representation_id: UUID) -> None:
        record = self._representation_or_404(representation_id)
        self.db.delete(record)
        self.db.commit()

    def list_credits(self, actor_profile_id: UUID | None = None) -> list[ActingCredit]:
        statement = select(ActingCredit).order_by(
            ActingCredit.section_order.asc(),
            ActingCredit.category.asc(),
            ActingCredit.display_order.asc(),
            ActingCredit.created_at.asc(),
        )
        if actor_profile_id:
            statement = statement.where(ActingCredit.actor_profile_id == actor_profile_id)
        return list(self.db.scalars(statement))

    def create_credit(self, payload: ActingCreditCreate) -> ActingCredit:
        self._actor_or_404(payload.actor_profile_id)
        record = ActingCredit(**payload.model_dump())
        self.db.add(record)
        self.db.flush()
        ResumePdfService(self.db).regenerate_for_actor(payload.actor_profile_id)
        self.db.commit()
        self.db.refresh(record)
        return record

    def update_credit(self, credit_id: UUID, payload: ActingCreditUpdate) -> ActingCredit:
        record = self._credit_or_404(credit_id)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(record, key, value)
        self.db.flush()
        ResumePdfService(self.db).regenerate_for_actor(record.actor_profile_id)
        self.db.commit()
        self.db.refresh(record)
        return record

    def delete_credit(self, credit_id: UUID) -> None:
        record = self._credit_or_404(credit_id)
        actor_profile_id = record.actor_profile_id
        self.db.delete(record)
        self.db.flush()
        ResumePdfService(self.db).regenerate_for_actor(actor_profile_id)
        self.db.commit()

    def generated_resume(self, actor_profile_id: UUID):
        self._actor_or_404(actor_profile_id)
        return ResumePdfService(self.db).current_generated_resume(actor_profile_id)

    def get_or_create_generated_resume(self, actor_profile_id: UUID, file_type: str = "pdf"):
        self._actor_or_404(actor_profile_id)
        service = ResumePdfService(self.db)
        asset = (
            service.current_generated_resume_docx(actor_profile_id)
            if file_type == "docx"
            else service.current_generated_resume(actor_profile_id)
        )
        if not asset:
            service.regenerate_for_actor(actor_profile_id)
            self.db.commit()
            asset = (
                service.current_generated_resume_docx(actor_profile_id)
                if file_type == "docx"
                else service.current_generated_resume(actor_profile_id)
            )
        if not asset:
            raise ValueError("Generated resume could not be created")
        return asset

    def _actor_or_404(self, actor_profile_id: UUID) -> ActorProfile:
        actor = self.db.get(ActorProfile, actor_profile_id)
        if not actor:
            raise NotFoundError("Actor profile not found")
        return actor

    def _representation_or_404(self, representation_id: UUID) -> Representation:
        record = self.db.get(Representation, representation_id)
        if not record:
            raise NotFoundError("Representation not found")
        return record

    def _credit_or_404(self, credit_id: UUID) -> ActingCredit:
        record = self.db.get(ActingCredit, credit_id)
        if not record:
            raise NotFoundError("Acting credit not found")
        return record
