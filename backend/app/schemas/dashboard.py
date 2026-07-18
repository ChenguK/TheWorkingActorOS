from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import TimestampedModel


class DashboardWidgetRead(TimestampedModel):
    actor_profile_id: UUID | None = None
    widget_id: str
    display_name: str
    enabled: bool
    sort_order: int
    size: str


class DashboardWidgetUpdate(BaseModel):
    widget_id: str
    enabled: bool | None = None
    sort_order: int | None = Field(default=None, ge=0)
    size: str | None = None


class DashboardWidgetBulkUpdate(BaseModel):
    widgets: list[DashboardWidgetUpdate]


class FocusModePreferenceRead(TimestampedModel):
    actor_profile_id: UUID | None = None
    active_mode: str


class FocusModePreferenceUpdate(BaseModel):
    active_mode: str
