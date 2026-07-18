from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import TimestampedModel


class DiscoveryProviderSettingsRead(TimestampedModel):
    provider_key: str
    display_name: str
    tier: int
    category: str
    source_type: str
    enabled: bool
    poll_frequency_minutes: int
    priority: int
    authentication_method: str
    supported_authentication_methods: list
    reliability_score: float
    notes: str | None = None
    provider_metadata: dict
    health_status: str
    health_message: str | None = None
    last_health_check_at: datetime | None = None


class DiscoveryProviderSettingsUpdate(BaseModel):
    enabled: bool | None = None
    poll_frequency_minutes: int | None = Field(default=None, ge=0)
    priority: int | None = Field(default=None, ge=0)
    authentication_method: str | None = None
    notes: str | None = None


class DiscoverySettingsRead(TimestampedModel):
    film_tv_breakdown_limit: int
    theater_breakdown_limit: int
    commercial_breakdown_limit: int
    voiceover_breakdown_limit: int


class DiscoverySettingsUpdate(BaseModel):
    film_tv_breakdown_limit: int | None = Field(default=None, ge=0)
    theater_breakdown_limit: int | None = Field(default=None, ge=0)
    commercial_breakdown_limit: int | None = Field(default=None, ge=0)
    voiceover_breakdown_limit: int | None = Field(default=None, ge=0)


class SourceResearchItemBase(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    source_url: str | None = Field(default=None, max_length=1000)
    base_url: str | None = Field(default=None, max_length=1000)
    suggested_specific_url: str | None = Field(default=None, max_length=1000)
    approved_discovery_url: str | None = Field(default=None, max_length=1000)
    category: str
    status: str = "Suggested"
    reliability_notes: str | None = None
    user_rating: int | None = Field(default=None, ge=1, le=5)
    last_researched_date: datetime | None = None
    last_checked_date: datetime | None = None
    notes: str | None = None
    suggested_by_ai: bool = False
    approved_by_user: bool = False
    deleted: bool = False
    deleted_at: datetime | None = None
    rejection_reason: str | None = None
    rejected_by_user: bool = False
    previous_status: str | None = None
    source_health: str = "Unchecked"
    suggested_classification: str = "Needs Review"
    health_reason: str | None = None
    http_status: int | None = None
    page_title: str | None = None
    redirect_target: str | None = None
    visible_text_excerpt: str | None = None
    organization_name: str | None = None
    submitted_url: str | None = None
    final_resolved_url: str | None = None
    url_health_status: str = "Unchecked"
    organization_legitimacy: str = "Unverified Organization"
    source_usefulness: str = "Needs Review"
    source_classification: str = "Needs Review"
    verification_notes: str | None = None
    discovered_from_breakdown_id: UUID | None = None
    discovery_reason: str | None = None
    source_role_match_count: int = 0


class SourceResearchItemCreate(SourceResearchItemBase):
    pass


class SourceResearchItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=180)
    source_url: str | None = Field(default=None, max_length=1000)
    base_url: str | None = Field(default=None, max_length=1000)
    suggested_specific_url: str | None = Field(default=None, max_length=1000)
    approved_discovery_url: str | None = Field(default=None, max_length=1000)
    category: str | None = None
    status: str | None = None
    reliability_notes: str | None = None
    user_rating: int | None = Field(default=None, ge=1, le=5)
    last_researched_date: datetime | None = None
    last_checked_date: datetime | None = None
    notes: str | None = None
    approved_by_user: bool | None = None
    rejection_reason: str | None = None
    source_health: str | None = None
    suggested_classification: str | None = None
    health_reason: str | None = None
    organization_name: str | None = None
    submitted_url: str | None = None
    final_resolved_url: str | None = None
    url_health_status: str | None = None
    organization_legitimacy: str | None = None
    source_usefulness: str | None = None
    source_classification: str | None = None
    verification_notes: str | None = None
    discovered_from_breakdown_id: UUID | None = None
    discovery_reason: str | None = None
    source_role_match_count: int | None = Field(default=None, ge=0)


class SourceResearchReject(BaseModel):
    rejection_reason: str | None = None


class SourceResearchItemRead(SourceResearchItemBase, TimestampedModel):
    provider_key: str | None = None
    added_to_discovery_at: datetime | None = None
