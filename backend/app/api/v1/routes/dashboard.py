from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.dashboard import (
    DashboardWidgetBulkUpdate,
    DashboardWidgetRead,
    FocusModePreferenceRead,
    FocusModePreferenceUpdate,
)
from app.services.dashboard_service import DashboardService

router = APIRouter()


@router.get("/widgets", response_model=list[DashboardWidgetRead])
def list_dashboard_widgets(
    actor_profile_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return DashboardService(db).list_widgets(actor_profile_id)


@router.put("/widgets", response_model=list[DashboardWidgetRead])
def update_dashboard_widgets(
    payload: DashboardWidgetBulkUpdate,
    actor_profile_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
):
    updates = [widget.model_dump(exclude_unset=True) for widget in payload.widgets]
    return DashboardService(db).update_widgets(updates, actor_profile_id)


@router.post("/widgets/reset", response_model=list[DashboardWidgetRead])
def reset_dashboard_widgets(
    actor_profile_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return DashboardService(db).reset_widgets(actor_profile_id)


@router.get("/focus-mode", response_model=FocusModePreferenceRead)
def get_focus_mode(
    actor_profile_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return DashboardService(db).get_focus_mode(actor_profile_id)


@router.put("/focus-mode", response_model=FocusModePreferenceRead)
def update_focus_mode(
    payload: FocusModePreferenceUpdate,
    actor_profile_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return DashboardService(db).update_focus_mode(payload.active_mode, actor_profile_id)
