from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import NotFoundError
from app.db.models import MaterialGapAlert, OutcomeNudge, SelfTapeWorkflow
from app.schemas.agent import (
    ActorCommandCenterRead,
    AssetPerformanceRead,
    MaterialGapAlertRead,
    SelfTapeWorkflowCreate,
    SelfTapeWorkflowRead,
    SelfTapeWorkflowUpdate,
)
from app.services.command_center_service import CommandCenterService
from app.services.actor_work_event_service import ActorWorkEventService

router = APIRouter()


@router.get("", response_model=ActorCommandCenterRead)
def get_command_center(db: Session = Depends(get_db)):
    return CommandCenterService(db).snapshot()


@router.post("/refresh", response_model=ActorCommandCenterRead)
def refresh_command_center(db: Session = Depends(get_db)):
    service = CommandCenterService(db)
    service.refresh_signals()
    return service.snapshot()


@router.get("/asset-performance", response_model=list[AssetPerformanceRead])
def get_asset_performance(db: Session = Depends(get_db)):
    return CommandCenterService(db).asset_performance()


@router.get("/material-gaps", response_model=list[MaterialGapAlertRead])
def list_material_gaps(db: Session = Depends(get_db)):
    CommandCenterService(db).refresh_signals()
    return list(
        db.scalars(select(MaterialGapAlert).order_by(MaterialGapAlert.created_at.desc()))
    )


@router.post("/outcome-nudges/{nudge_id}/resolve")
def resolve_outcome_nudge(nudge_id: UUID, db: Session = Depends(get_db)):
    nudge = db.get(OutcomeNudge, nudge_id)
    if not nudge:
        raise NotFoundError("Outcome nudge not found")
    nudge.status = "Resolved"
    nudge.resolved_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "resolved"}


@router.get("/self-tapes", response_model=list[SelfTapeWorkflowRead])
def list_self_tapes(db: Session = Depends(get_db)):
    return CommandCenterService(db).list_self_tapes()


@router.post("/self-tapes", response_model=SelfTapeWorkflowRead, status_code=201)
def create_self_tape(payload: SelfTapeWorkflowCreate, db: Session = Depends(get_db)):
    workflow = SelfTapeWorkflow(**payload.model_dump())
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return workflow


@router.patch("/self-tapes/{workflow_id}", response_model=SelfTapeWorkflowRead)
def update_self_tape(workflow_id: UUID, payload: SelfTapeWorkflowUpdate, db: Session = Depends(get_db)):
    workflow = db.get(SelfTapeWorkflow, workflow_id)
    if not workflow:
        raise NotFoundError("Self-tape workflow not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(workflow, key, value)
    if payload.status == "Completed":
        ActorWorkEventService(db).self_tape_completed(workflow)
    db.commit()
    db.refresh(workflow)
    return workflow
