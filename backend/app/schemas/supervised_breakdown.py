from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import TimestampedModel
from app.schemas.opportunity import OpportunityRead


class SupervisedBrowserStart(BaseModel):
    platform_name: str = Field(pattern="^(Actors Access|Casting Networks|Casting Frontier)$")


class SupervisedBrowserStatus(BaseModel):
    available: bool = True
    active: bool
    platform_name: str | None = None
    current_url: str | None = None
    message: str


class SupervisedBreakdownImportRead(TimestampedModel):
    actor_profile_id: UUID | None = None
    approved_opportunity_id: UUID | None = None
    platform_name: str
    source_url: str | None = None
    imported_at: datetime
    raw_visible_text: str
    parsed_data_json: dict
    import_status: str
    user_approved: bool
    error_message: str | None = None


class SupervisedBreakdownImportUpdate(BaseModel):
    parsed_data_json: dict | None = None
    import_status: str | None = Field(
        default=None, pattern="^(Draft|Approved|Rejected|Needs Review|Blocked)$"
    )


class SupervisedBreakdownApproveRead(BaseModel):
    import_record: SupervisedBreakdownImportRead
    opportunity: OpportunityRead
