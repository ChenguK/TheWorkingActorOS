from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import TimestampedModel


class PlatformProfileImportCreate(BaseModel):
    actor_profile_id: UUID | None = None
    platform_name: str
    profile_url: str | None = Field(default=None, max_length=1000)
    import_method: str
    raw_import_text: str = Field(min_length=1)


class PlatformProfileUpdate(BaseModel):
    profile_url: str | None = Field(default=None, max_length=1000)
    raw_import_text: str | None = None
    import_status: str | None = None
    user_approved: bool | None = None
    parsed_profile: dict | None = None


class PlatformProfileRead(TimestampedModel):
    actor_profile_id: UUID | None = None
    platform_name: str
    profile_url: str | None = None
    imported_at: datetime
    import_method: str
    raw_import_text: str
    import_status: str
    user_approved: bool
    parsed_profile: dict


class PlatformAssetMappingBase(BaseModel):
    platform_name: str
    platform_asset_name: str = Field(min_length=1, max_length=255)
    asset_type: str
    local_asset_id: UUID | None = None
    tags: list[str] = []
    archetypes: list[str] = []
    notes: str | None = None


class PlatformAssetMappingCreate(PlatformAssetMappingBase):
    pass


class PlatformAssetMappingUpdate(BaseModel):
    platform_name: str | None = None
    platform_asset_name: str | None = Field(default=None, min_length=1, max_length=255)
    asset_type: str | None = None
    local_asset_id: UUID | None = None
    tags: list[str] | None = None
    archetypes: list[str] | None = None
    notes: str | None = None


class PlatformAssetMappingRead(PlatformAssetMappingBase, TimestampedModel):
    pass


class PlatformImportApproveRead(BaseModel):
    platform_profile: PlatformProfileRead
    created_mappings: list[PlatformAssetMappingRead]
    compliance_note: str


class PublicProfileImportCreate(BaseModel):
    platform_name: str
    profile_url: str = Field(min_length=1, max_length=1000)


class PublicProfileImportUpdate(BaseModel):
    raw_visible_text: str | None = None
    parsed_data_json: dict | None = None
    import_status: str | None = None
    user_approved: bool | None = None
    error_message: str | None = None


class PublicProfileImportRead(TimestampedModel):
    platform_name: str
    profile_url: str
    import_method: str
    imported_at: datetime
    raw_visible_text: str
    parsed_data_json: dict
    import_status: str
    user_approved: bool
    error_message: str | None = None


class PublicProfileImportApproveRead(BaseModel):
    public_profile_import: PublicProfileImportRead
    created_mappings: list[PlatformAssetMappingRead]
    compliance_note: str
