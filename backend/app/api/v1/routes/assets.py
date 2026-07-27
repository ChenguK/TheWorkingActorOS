import json
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.agents.asset_analysis_agent import AssetAnalysisAgent
from app.schemas.asset import AssetRead, AssetUpdate
from app.services.asset_service import AssetService
from app.services.file_storage_service import (
    FileStorageService,
    PersistentFileStorageUnavailableError,
    require_persistent_file_storage,
)

router = APIRouter()


def parse_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except json.JSONDecodeError:
        pass
    return [item.strip() for item in value.split(",") if item.strip()]


@router.get("", response_model=list[AssetRead])
def list_assets(actor_profile_id: UUID | None = None, db: Session = Depends(get_db)):
    return AssetService(db).list(actor_profile_id)


@router.post("", response_model=AssetRead, status_code=201)
def create_asset(
    actor_profile_id: UUID = Form(...),
    asset_name: str = Form(...),
    asset_type: str = Form(...),
    description: str | None = Form(None),
    tags: str | None = Form(None),
    archetype_names: str | None = Form(None),
    career_task_id: UUID | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    try:
        require_persistent_file_storage()
        return AssetService(db).create(
            actor_profile_id=actor_profile_id,
            asset_name=asset_name,
            asset_type=asset_type,
            description=description,
            tags=parse_list(tags),
            archetype_names=parse_list(archetype_names),
            upload=file,
            career_task_id=career_task_id,
        )
    except PersistentFileStorageUnavailableError as exc:
        raise persistent_storage_unavailable() from exc


@router.get("/{asset_id}", response_model=AssetRead)
def get_asset(asset_id: UUID, db: Session = Depends(get_db)):
    return AssetService(db).get(asset_id)


@router.get("/{asset_id}/file")
def view_asset_file(asset_id: UUID, db: Session = Depends(get_db)):
    asset = AssetService(db).get(asset_id)
    try:
        path = FileStorageService().existing_file(asset.local_file_path)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "asset_file_not_found",
                "message": "The stored file is unavailable.",
            },
        ) from exc
    return FileResponse(
        path,
        media_type=asset.mime_type,
        filename=asset.original_filename or asset.asset_name,
    )


@router.post("/{asset_id}/analyze", response_model=AssetRead)
def analyze_asset(asset_id: UUID, db: Session = Depends(get_db)):
    asset = AssetService(db).get(asset_id)
    return AssetAnalysisAgent(db).analyze(asset)


@router.patch("/{asset_id}", response_model=AssetRead)
def update_asset(asset_id: UUID, payload: AssetUpdate, db: Session = Depends(get_db)):
    return AssetService(db).update(asset_id, payload)


@router.delete("/{asset_id}", status_code=204)
def delete_asset(asset_id: UUID, db: Session = Depends(get_db)):
    try:
        require_persistent_file_storage()
        AssetService(db).delete(asset_id)
    except PersistentFileStorageUnavailableError as exc:
        raise persistent_storage_unavailable() from exc


def persistent_storage_unavailable() -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={
            "code": "persistent_file_storage_unavailable",
            "message": ("File mutations are disabled because durable storage is not configured."),
        },
    )
