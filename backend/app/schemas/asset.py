from uuid import UUID
from datetime import date

from pydantic import BaseModel, Field

from app.schemas.common import TimestampedModel


AssetType = str


class ArchetypeRead(TimestampedModel):
    name: str
    slug: str
    description: str | None = None


class AssetBase(BaseModel):
    actor_profile_id: UUID
    asset_name: str = Field(min_length=1, max_length=255)
    asset_type: AssetType
    description: str | None = None
    tags: list[str] = []
    archetype_names: list[str] = []
    upload_date: date | None = None
    last_used_date: date | None = None
    last_updated_date: date | None = None
    expiration_warning_date: date | None = None
    freshness_status: str = "Current"


class AssetCreate(AssetBase):
    pass


class AssetUpdate(BaseModel):
    asset_name: str | None = Field(default=None, min_length=1, max_length=255)
    asset_type: AssetType | None = None
    description: str | None = None
    tags: list[str] | None = None
    archetype_names: list[str] | None = None
    upload_date: date | None = None
    last_used_date: date | None = None
    last_updated_date: date | None = None
    expiration_warning_date: date | None = None
    freshness_status: str | None = None


class AssetRead(AssetBase, TimestampedModel):
    local_file_path: str
    original_filename: str | None = None
    mime_type: str | None = None
    file_size_bytes: int | None = None
    ai_suggested_tags: list[str] = []
    ai_suggested_archetypes: list[str] = []
    analysis_status: str = "pending"
    analysis_explanation: str | None = None
