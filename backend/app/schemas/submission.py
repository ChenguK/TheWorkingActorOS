from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.core.constants import SUBMISSION_STATUSES
from app.schemas.asset import AssetRead
from app.schemas.common import ORMModel, TimestampedModel
from app.schemas.opportunity import OpportunityRead


class SubmissionStatusHistoryCreate(BaseModel):
    status: str
    notes: str | None = None
    occurred_at: datetime | None = None


class SubmissionStatusHistoryRead(ORMModel):
    id: UUID
    status: str
    notes: str | None
    occurred_at: datetime


class SubmissionCreate(BaseModel):
    actor_profile_id: UUID
    opportunity_id: UUID
    asset_ids: list[UUID] = []
    current_status: str = "Submitted"
    notes: str | None = None
    submitted_at: datetime | None = None
    submission_fee: float = 0
    media_fee: float = 0
    travel_cost: float = 0
    housing_cost: float = 0
    parking_cost: float = 0
    other_cost: float = 0


class SubmissionUpdate(BaseModel):
    opportunity_id: UUID | None = None
    asset_ids: list[UUID] | None = None
    current_status: str | None = None
    notes: str | None = None
    submitted_at: datetime | None = None
    submission_fee: float | None = None
    media_fee: float | None = None
    travel_cost: float | None = None
    housing_cost: float | None = None
    parking_cost: float | None = None
    other_cost: float | None = None


class SubmissionRead(TimestampedModel):
    actor_profile_id: UUID
    opportunity_id: UUID
    current_status: str
    notes: str | None = None
    submitted_at: datetime | None = None
    submission_fee: float = 0
    media_fee: float = 0
    travel_cost: float = 0
    housing_cost: float = 0
    parking_cost: float = 0
    other_cost: float = 0
    total_cost: float = 0
    opportunity: OpportunityRead | None = None
    assets: list[AssetRead] = []
    status_history: list[SubmissionStatusHistoryRead] = []
