from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.supervised_breakdown import (
    SupervisedBreakdownApproveRead,
    SupervisedBreakdownImportRead,
    SupervisedBreakdownImportUpdate,
    SupervisedBrowserStart,
    SupervisedBrowserStatus,
)
from app.services.supervised_breakdown_import_service import (
    SupervisedBreakdownImportService,
    SupervisedBrowserDisabledError,
)

router = APIRouter()


@router.get("", response_model=list[SupervisedBreakdownImportRead])
def list_supervised_imports(db: Session = Depends(get_db)):
    return SupervisedBreakdownImportService(db).list_imports()


@router.post("/browser/start", response_model=SupervisedBrowserStatus)
def start_supervised_browser(payload: SupervisedBrowserStart, db: Session = Depends(get_db)):
    try:
        return SupervisedBreakdownImportService(db).start_browser(payload.platform_name)
    except SupervisedBrowserDisabledError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "supervised_browser_disabled",
                "message": str(exc),
            },
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/browser/status", response_model=SupervisedBrowserStatus)
def supervised_browser_status(db: Session = Depends(get_db)):
    return SupervisedBreakdownImportService(db).browser_status()


@router.post("/browser/close", response_model=SupervisedBrowserStatus)
def close_supervised_browser(db: Session = Depends(get_db)):
    return SupervisedBreakdownImportService(db).close_browser()


@router.post("/import-current-page", response_model=SupervisedBreakdownImportRead, status_code=201)
def import_current_supervised_page(db: Session = Depends(get_db)):
    try:
        return SupervisedBreakdownImportService(db).import_current_page()
    except SupervisedBrowserDisabledError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "supervised_browser_disabled",
                "message": str(exc),
            },
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=409,
            detail="This platform blocked automated extraction. Use copy/paste, screenshot, PDF, or manual entry instead.",
        ) from exc


@router.patch("/{import_id}", response_model=SupervisedBreakdownImportRead)
def update_supervised_import(
    import_id: UUID,
    payload: SupervisedBreakdownImportUpdate,
    db: Session = Depends(get_db),
):
    return SupervisedBreakdownImportService(db).update_import(import_id, payload)


@router.post("/{import_id}/approve", response_model=SupervisedBreakdownApproveRead)
def approve_supervised_import(import_id: UUID, db: Session = Depends(get_db)):
    try:
        record, opportunity = SupervisedBreakdownImportService(db).approve_import(import_id)
        return {"import_record": record, "opportunity": opportunity}
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{import_id}/reject", response_model=SupervisedBreakdownImportRead)
def reject_supervised_import(import_id: UUID, db: Session = Depends(get_db)):
    return SupervisedBreakdownImportService(db).reject_import(import_id)


@router.delete("/{import_id}", status_code=204)
def delete_supervised_import(import_id: UUID, db: Session = Depends(get_db)):
    SupervisedBreakdownImportService(db).delete_import(import_id)
