from pydantic import BaseModel, Field, model_validator

from app.schemas.common import TimestampedModel


class ActorProfileFields(BaseModel):
    name: str
    sag_status: str
    union_status: str
    current_location: str
    playable_age_min: int
    playable_age_max: int
    secondary_playable_age_min: int | None = None
    secondary_playable_age_max: int | None = None
    skills: list[str] = []
    gender_identities: list[str] = []
    gender_expression: str | None = None
    pronouns: str | None = None
    ethnicities: list[str] = []
    racial_identities: list[str] = []
    nationalities: list[str] = []
    languages: list[str] = []
    accents: list[str] = []
    disability_identities: list[str] = []
    included_role_types: list[str] = []
    excluded_role_types: list[str] = []
    accessibility_notes: str | None = None
    demographic_notes: str | None = None
    notes: str | None = None


class ActorProfileCreate(ActorProfileFields):
    @model_validator(mode="after")
    def validate_age_ranges(self):
        if (
            self.playable_age_min is not None
            and self.playable_age_max is not None
            and self.playable_age_min > self.playable_age_max
        ):
            raise ValueError("Playable age minimum must be less than or equal to maximum")
        if (
            self.secondary_playable_age_min is not None
            and self.secondary_playable_age_max is not None
            and self.secondary_playable_age_min > self.secondary_playable_age_max
        ):
            raise ValueError("Secondary playable age minimum must be less than or equal to maximum")
        return self


class ActorProfileUpdate(ActorProfileCreate):
    name: str | None = Field(default=None)
    sag_status: str | None = None
    union_status: str | None = None
    current_location: str | None = None
    playable_age_min: int | None = None
    playable_age_max: int | None = None


class ActorProfileBase(ActorProfileFields, TimestampedModel):
    pass
