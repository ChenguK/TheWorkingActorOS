from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import TimestampedModel


class RepresentationBase(BaseModel):
    actor_profile_id: UUID
    agency_name: str = Field(min_length=1, max_length=255)
    agent_name: str | None = Field(default=None, max_length=255)
    agent_email: str | None = Field(default=None, max_length=255)
    agent_phone: str | None = Field(default=None, max_length=80)
    agency_website: str | None = Field(default=None, max_length=1000)
    representation_type: str
    market: list[str] = []
    notes: str | None = None
    active: bool = True
    start_date: date | None = None
    end_date: date | None = None


class RepresentationCreate(RepresentationBase):
    pass


class RepresentationUpdate(BaseModel):
    agency_name: str | None = Field(default=None, min_length=1, max_length=255)
    agent_name: str | None = Field(default=None, max_length=255)
    agent_email: str | None = Field(default=None, max_length=255)
    agent_phone: str | None = Field(default=None, max_length=80)
    agency_website: str | None = Field(default=None, max_length=1000)
    representation_type: str | None = None
    market: list[str] | None = None
    notes: str | None = None
    active: bool | None = None
    start_date: date | None = None
    end_date: date | None = None


class RepresentationRead(RepresentationBase, TimestampedModel):
    pass


class ActingCreditBase(BaseModel):
    actor_profile_id: UUID
    category: str
    section_enabled: bool = True
    section_order: int = 0
    display_order: int = 0
    highlighted: bool = False
    project_title: str | None = Field(default=None, max_length=255)
    role_or_character: str | None = Field(default=None, max_length=255)
    role_type: str | None = Field(default=None, max_length=120)
    production_company: str | None = Field(default=None, max_length=255)
    network_or_distributor: str | None = Field(default=None, max_length=255)
    director: str | None = Field(default=None, max_length=255)
    episode_title: str | None = Field(default=None, max_length=255)
    season_episode: str | None = Field(default=None, max_length=80)
    year: str | None = Field(default=None, max_length=20)
    union_status: str | None = Field(default=None, max_length=80)
    class_or_program: str | None = Field(default=None, max_length=255)
    instructor: str | None = Field(default=None, max_length=255)
    institution: str | None = Field(default=None, max_length=255)
    skill_name: str | None = Field(default=None, max_length=255)
    skill_category: str | None = Field(default=None, max_length=120)
    proficiency: str | None = Field(default=None, max_length=80)
    notes: str | None = None


class ActingCreditCreate(ActingCreditBase):
    pass


class ActingCreditUpdate(BaseModel):
    category: str | None = None
    section_enabled: bool | None = None
    section_order: int | None = None
    display_order: int | None = None
    highlighted: bool | None = None
    project_title: str | None = Field(default=None, max_length=255)
    role_or_character: str | None = Field(default=None, max_length=255)
    role_type: str | None = Field(default=None, max_length=120)
    production_company: str | None = Field(default=None, max_length=255)
    network_or_distributor: str | None = Field(default=None, max_length=255)
    director: str | None = Field(default=None, max_length=255)
    episode_title: str | None = Field(default=None, max_length=255)
    season_episode: str | None = Field(default=None, max_length=80)
    year: str | None = Field(default=None, max_length=20)
    union_status: str | None = Field(default=None, max_length=80)
    class_or_program: str | None = Field(default=None, max_length=255)
    instructor: str | None = Field(default=None, max_length=255)
    institution: str | None = Field(default=None, max_length=255)
    skill_name: str | None = Field(default=None, max_length=255)
    skill_category: str | None = Field(default=None, max_length=120)
    proficiency: str | None = Field(default=None, max_length=80)
    notes: str | None = None


class ActingCreditRead(ActingCreditBase, TimestampedModel):
    pass
