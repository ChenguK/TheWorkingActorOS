from __future__ import annotations

from datetime import date, timedelta

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.db.models import Asset
from app.repositories.asset import AssetRepository
from app.schemas.asset import AssetUpdate
from app.services.actor_work_event_service import ActorWorkEventService
from app.services.file_storage_service import FileStorageService
from app.services.workflow_connector_service import WorkflowConnectorService


class AssetService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = AssetRepository(db)
        self.storage = FileStorageService()

    def list(self, actor_profile_id=None) -> list[Asset]:
        if actor_profile_id:
            return self.repo.list_by_actor(actor_profile_id)
        return self.repo.list()

    def create(
        self,
        *,
        actor_profile_id,
        asset_name: str,
        asset_type: str,
        description: str | None,
        tags: list[str],
        archetype_names: list[str],
        upload: UploadFile,
        career_task_id=None,
    ) -> Asset:
        path, size = self.storage.save_upload(upload)
        today = date.today()
        asset = Asset(
            actor_profile_id=actor_profile_id,
            asset_name=asset_name,
            asset_type=asset_type,
            description=description,
            tags=tags,
            archetype_names=archetype_names,
            local_file_path=path,
            original_filename=upload.filename,
            mime_type=upload.content_type,
            file_size_bytes=size,
            upload_date=today,
            last_updated_date=today,
            expiration_warning_date=self._warning_date(asset_type, today),
            freshness_status="Current",
        )
        asset = self.repo.add(asset)
        self.db.flush()
        WorkflowConnectorService(self.db).after_asset_created(asset, career_task_id)
        ActorWorkEventService(self.db).material_uploaded(asset, career_task_id=career_task_id)
        self.db.commit()
        return asset

    def get(self, asset_id) -> Asset:
        return self.repo.get(asset_id)

    def update(self, asset_id, payload: AssetUpdate) -> Asset:
        asset = self.repo.get(asset_id)
        data = payload.model_dump(exclude_unset=True)
        if data:
            data.setdefault("last_updated_date", date.today())
        asset = self.repo.apply_updates(asset, data)
        self._apply_freshness(asset)
        if asset.asset_type == "Resume":
            ActorWorkEventService(self.db).resume_updated(asset)
        self.db.commit()
        return asset

    def delete(self, asset_id) -> None:
        asset = self.repo.get(asset_id)
        path = asset.local_file_path
        self.repo.delete(asset)
        self.db.commit()
        self.storage.delete_file(path)

    def _warning_date(self, asset_type: str, start: date) -> date:
        if asset_type == "Headshot":
            return start + timedelta(days=18 * 30)
        if asset_type == "Reel":
            return start + timedelta(days=24 * 30)
        return start + timedelta(days=180)

    def _apply_freshness(self, asset: Asset) -> None:
        today = date.today()
        reference = asset.last_updated_date or asset.upload_date or today
        age_days = (today - reference).days
        unused_days = (today - asset.last_used_date).days if asset.last_used_date else None
        if asset.asset_type == "Headshot" and age_days >= 18 * 30:
            asset.freshness_status = "Outdated"
        elif asset.asset_type == "Reel" and age_days >= 24 * 30:
            asset.freshness_status = "Outdated"
        elif asset.asset_type == "Resume" and age_days >= 180:
            asset.freshness_status = "Needs Review"
        elif unused_days is not None and unused_days >= 180:
            asset.freshness_status = "Needs Review"
        elif age_days >= 365:
            asset.freshness_status = "Aging"
        else:
            asset.freshness_status = "Current"
