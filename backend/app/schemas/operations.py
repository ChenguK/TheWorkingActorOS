from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import TimestampedModel


class AuditionCalendarEventBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    event_type: str
    opportunity_id: UUID | None = None
    submission_id: UUID | None = None
    start_datetime: datetime
    end_datetime: datetime | None = None
    location: str | None = None
    is_virtual: bool = False
    notes: str | None = None


class AuditionCalendarEventCreate(AuditionCalendarEventBase):
    pass


class AuditionCalendarEventUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    event_type: str | None = None
    opportunity_id: UUID | None = None
    submission_id: UUID | None = None
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    location: str | None = None
    is_virtual: bool | None = None
    notes: str | None = None


class AuditionCalendarEventRead(AuditionCalendarEventBase, TimestampedModel):
    pass


class OperationsAlert(BaseModel):
    alert_type: str
    severity: str
    title: str
    message: str
    related_id: UUID | None = None


class CostDashboardRead(BaseModel):
    total_spent: float
    cost_per_callback: float
    cost_per_booking: float
    costs_by_platform: dict[str, float]
    costs_by_archetype: dict[str, float]
    subscriptions: dict[str, float] = {}
    subscription_monthly_total: float = 0
    subscription_annual_total: float = 0
    estimated_monthly_subscription_spend: float = 0
    submission_fees_total: float = 0
    media_fees_total: float = 0
    travel_housing_total: float = 0
    other_costs_total: float = 0


class FreshnessWarningRead(BaseModel):
    asset_id: UUID
    asset_name: str
    asset_type: str
    freshness_status: str
    message: str


class OperationsDashboardRead(BaseModel):
    alerts: list[OperationsAlert]
    upcoming_events: list[AuditionCalendarEventRead]
    cost_dashboard: CostDashboardRead
    freshness_warnings: list[FreshnessWarningRead]


class AvailabilityBlockBase(BaseModel):
    actor_profile_id: UUID | None = None
    start_date: datetime
    end_date: datetime
    block_type: str = "Personal Commitment"
    title: str = Field(min_length=1, max_length=255)
    notes: str | None = None


class AvailabilityBlockCreate(AvailabilityBlockBase):
    pass


class AvailabilityBlockUpdate(BaseModel):
    actor_profile_id: UUID | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    block_type: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    notes: str | None = None


class AvailabilityBlockRead(AvailabilityBlockBase, TimestampedModel):
    pass


class ProfessionalEquipmentProfileBase(BaseModel):
    actor_profile_id: UUID | None = None
    cameras: list[str] = []
    lighting: list[str] = []
    audio_equipment: list[str] = []
    backdrops: list[str] = []
    editing_software: list[str] = []
    teleprompter: bool = False
    reader_availability: str | None = None
    internet_upload_speed: str | None = None
    home_audition_space: str | None = None
    notes: str | None = None


class ProfessionalEquipmentProfileUpdate(ProfessionalEquipmentProfileBase):
    pass


class ProfessionalEquipmentProfileRead(ProfessionalEquipmentProfileBase, TimestampedModel):
    pass


class CastingPlatformSubscriptionBase(BaseModel):
    platform_name: str = Field(min_length=1, max_length=120)
    has_subscription: bool = False
    subscription_level: str | None = None
    monthly_cost: float | None = None
    annual_cost: float | None = None
    renewal_date: date | None = None
    notes: str | None = None
    active: bool = True


class CastingPlatformSubscriptionCreate(CastingPlatformSubscriptionBase):
    pass


class CastingPlatformSubscriptionUpdate(BaseModel):
    platform_name: str | None = Field(default=None, min_length=1, max_length=120)
    has_subscription: bool | None = None
    subscription_level: str | None = None
    monthly_cost: float | None = None
    annual_cost: float | None = None
    renewal_date: date | None = None
    notes: str | None = None
    active: bool | None = None


class CastingPlatformSubscriptionRead(CastingPlatformSubscriptionBase, TimestampedModel):
    pass


class DailyPlatformCheckInBase(BaseModel):
    platform_subscription_id: UUID
    check_date: date
    timezone: str = "America/New_York"
    checked_today: bool = False
    checked_at: datetime | None = None
    notes: str | None = None


class DailyPlatformCheckInUpdate(BaseModel):
    checked_today: bool | None = None
    notes: str | None = None
    timezone: str | None = None


class DailyPlatformCheckInRead(DailyPlatformCheckInBase, TimestampedModel):
    platform_name: str
    has_subscription: bool
    subscription_level: str | None = None
    active: bool
