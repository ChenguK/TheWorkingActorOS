from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.platform import (
    PlatformAssetMappingCreate,
    PlatformAssetMappingRead,
    PlatformAssetMappingUpdate,
    PlatformImportApproveRead,
    PlatformProfileImportCreate,
    PlatformProfileRead,
    PlatformProfileUpdate,
    PublicProfileImportApproveRead,
    PublicProfileImportCreate,
    PublicProfileImportRead,
    PublicProfileImportUpdate,
)
from app.services.platform_import_service import PlatformImportService

router = APIRouter()


@router.get("/profiles", response_model=list[PlatformProfileRead])
def list_platform_profiles(db: Session = Depends(get_db)):
    return PlatformImportService(db).list_profiles()


@router.get("/public-profiles", response_model=list[PublicProfileImportRead])
def list_public_profile_imports(db: Session = Depends(get_db)):
    return PlatformImportService(db).list_public_imports()


@router.post("/public-profiles/import-url", response_model=PublicProfileImportRead, status_code=201)
def import_public_profile_url(
    payload: PublicProfileImportCreate,
    db: Session = Depends(get_db),
):
    return PlatformImportService(db).import_public_profile_url(payload)


@router.patch("/public-profiles/{import_id}", response_model=PublicProfileImportRead)
def update_public_profile_import(
    import_id: UUID,
    payload: PublicProfileImportUpdate,
    db: Session = Depends(get_db),
):
    return PlatformImportService(db).update_public_import(import_id, payload)


@router.post("/public-profiles/{import_id}/approve", response_model=PublicProfileImportApproveRead)
def approve_public_profile_import(import_id: UUID, db: Session = Depends(get_db)):
    try:
        record, mappings = PlatformImportService(db).approve_public_import(import_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "public_profile_import": record,
        "created_mappings": mappings,
        "compliance_note": "Approved data came from visible public/shareable page text only. This app did not log in, bypass authentication, download protected media, crawl in the background, or scrape hidden account data.",
    }


@router.post("/public-profiles/{import_id}/reject", response_model=PublicProfileImportRead)
def reject_public_profile_import(import_id: UUID, db: Session = Depends(get_db)):
    return PlatformImportService(db).reject_public_import(import_id)


@router.delete("/public-profiles/{import_id}", status_code=204)
def delete_public_profile_import(import_id: UUID, db: Session = Depends(get_db)):
    PlatformImportService(db).delete_public_import(import_id)
    return None


@router.post("/profiles/import-text", response_model=PlatformProfileRead, status_code=201)
def import_platform_profile_text(
    payload: PlatformProfileImportCreate,
    db: Session = Depends(get_db),
):
    return PlatformImportService(db).import_from_text(payload)


@router.post("/profiles/import-upload", response_model=PlatformProfileRead, status_code=201)
def import_platform_profile_upload(
    platform_name: str = Form(...),
    import_method: str = Form(...),
    actor_profile_id: UUID | None = Form(None),
    profile_url: str | None = Form(None),
    raw_import_text: str | None = Form(None),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    try:
        return PlatformImportService(db).import_from_upload(
            actor_profile_id=actor_profile_id,
            platform_name=platform_name,
            profile_url=profile_url,
            import_method=import_method,
            upload=file,
            raw_import_text=raw_import_text,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/profiles/{profile_id}", response_model=PlatformProfileRead)
def update_platform_profile(
    profile_id: UUID,
    payload: PlatformProfileUpdate,
    db: Session = Depends(get_db),
):
    return PlatformImportService(db).update_profile(profile_id, payload)


@router.post("/profiles/{profile_id}/approve", response_model=PlatformImportApproveRead)
def approve_platform_profile(profile_id: UUID, db: Session = Depends(get_db)):
    profile, mappings = PlatformImportService(db).approve_profile(profile_id)
    return {
        "platform_profile": profile,
        "created_mappings": mappings,
        "compliance_note": "Approved data came from user-provided imports only. This app does not scrape logged-in casting platform pages or download protected media.",
    }


@router.post("/profiles/{profile_id}/reject", response_model=PlatformProfileRead)
def reject_platform_profile(profile_id: UUID, db: Session = Depends(get_db)):
    return PlatformImportService(db).reject_profile(profile_id)


@router.delete("/profiles/{profile_id}", status_code=204)
def delete_platform_profile(profile_id: UUID, db: Session = Depends(get_db)):
    PlatformImportService(db).delete_profile(profile_id)
    return None


@router.get("/asset-mappings", response_model=list[PlatformAssetMappingRead])
def list_platform_asset_mappings(db: Session = Depends(get_db)):
    return PlatformImportService(db).list_mappings()


@router.post("/asset-mappings", response_model=PlatformAssetMappingRead, status_code=201)
def create_platform_asset_mapping(
    payload: PlatformAssetMappingCreate,
    db: Session = Depends(get_db),
):
    return PlatformImportService(db).create_mapping(payload)


@router.patch("/asset-mappings/{mapping_id}", response_model=PlatformAssetMappingRead)
def update_platform_asset_mapping(
    mapping_id: UUID,
    payload: PlatformAssetMappingUpdate,
    db: Session = Depends(get_db),
):
    return PlatformImportService(db).update_mapping(mapping_id, payload)


@router.delete("/asset-mappings/{mapping_id}", status_code=204)
def delete_platform_asset_mapping(mapping_id: UUID, db: Session = Depends(get_db)):
    PlatformImportService(db).delete_mapping(mapping_id)
    return None
