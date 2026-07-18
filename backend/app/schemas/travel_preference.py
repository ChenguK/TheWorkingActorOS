from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import TimestampedModel


class TravelPreferenceBase(BaseModel):
    actor_profile_id: UUID
    max_local_drive_time: int = Field(300, gt=0)
    extended_drive_time: int = Field(720, gt=0)
    flight_allowed: bool = True
    housing_required: bool = False
    international_allowed: bool = False
    audition_max_drive_time: int = Field(120, gt=0)
    audition_virtual_allowed: bool = True
    audition_self_tape_allowed: bool = True
    working_as_local_drive_time: int = Field(300, gt=0)
    working_as_local_housing_self_provided: bool = True
    require_travel_housing_over_local_drive: bool = True
    audition_notes: str | None = None
    working_notes: str | None = None

    @model_validator(mode="after")
    def validate_drive_times(self):
        if self.extended_drive_time < self.max_local_drive_time:
            raise ValueError("Extended drive time must be greater than or equal to local drive time")
        return self


class TravelPreferenceCreate(TravelPreferenceBase):
    pass


class TravelPreferenceUpdate(BaseModel):
    max_local_drive_time: int | None = Field(default=None, gt=0)
    extended_drive_time: int | None = Field(default=None, gt=0)
    flight_allowed: bool | None = None
    housing_required: bool | None = None
    international_allowed: bool | None = None
    audition_max_drive_time: int | None = Field(default=None, gt=0)
    audition_virtual_allowed: bool | None = None
    audition_self_tape_allowed: bool | None = None
    working_as_local_drive_time: int | None = Field(default=None, gt=0)
    working_as_local_housing_self_provided: bool | None = None
    require_travel_housing_over_local_drive: bool | None = None
    audition_notes: str | None = None
    working_notes: str | None = None


class TravelPreferenceRead(TravelPreferenceBase, TimestampedModel):
    pass
