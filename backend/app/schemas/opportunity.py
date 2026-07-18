from uuid import UUID
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.common import TimestampedModel


class OpportunitySourceRead(TimestampedModel):
    name: str
    source_type: str
    priority_rank: int
    is_enabled: bool


class CharacterProfileRead(TimestampedModel):
    breakdown_id: UUID
    breakdown_role_id: UUID
    role_name: str
    billing: str | None = None
    primary_archetypes: list = []
    secondary_archetypes: list = []
    archetype_confidence_scores: list = []
    personality_traits: list = []
    emotional_traits: list = []
    relationships: list = []
    motivations: list = []
    internal_conflict: str | None = None
    external_conflict: str | None = None
    emotional_arc: str | None = None
    genre: str | None = None
    comedic_level: int = 0
    dramatic_level: int = 0
    physical_requirements: list = []
    vocal_requirements: list = []
    movement_requirements: list = []
    casting_language: list = []
    recommended_materials: list = []
    ai_summary: str | None = None


class CastingLanguageRead(TimestampedModel):
    breakdown_id: UUID
    breakdown_role_id: UUID
    original_text: str
    billing: str | None = None
    age_range: str | None = None
    gender: str | None = None
    ethnicity: str | None = None
    union: str | None = None
    compensation: str | None = None
    special_notes: list = []


class BreakdownRoleRead(TimestampedModel):
    breakdown_id: UUID
    role_name: str
    role_type: str | None = None
    billing: str | None = None
    billing_or_role_type: str | None = None
    character_description: str | None = None
    gender_presentation: str | None = None
    ethnicity_or_cultural_background: str | None = None
    playable_age_min: int | None = None
    playable_age_max: int | None = None
    height_requirements: str | None = None
    vocal_requirements: str | None = None
    dance_requirements: str | None = None
    movement_requirements: str | None = None
    language_requirements: str | None = None
    special_skills: str | None = None
    preparation_notes: str | None = None
    union_status: str | None = None
    role_notes: str | None = None
    fit_status: str = "Needs Review"
    fit_score: int = 0
    fit_explanation: str | None = None
    confidence_score: int = 50
    extracted_facts: dict = {}
    ai_inference: dict = {}
    character_profile: CharacterProfileRead | None = None
    casting_language: CastingLanguageRead | None = None


class BreakdownSectionRead(TimestampedModel):
    breakdown_id: UUID
    section_type: str
    heading: str | None = None
    raw_text: str
    parsed_json: dict = {}
    confidence_score: int = 50
    display_order: int = 0


class BreakdownParseRunRead(TimestampedModel):
    breakdown_id: UUID
    parser_version: str
    parse_mode: str
    started_at: datetime
    completed_at: datetime | None = None
    status: str
    overall_confidence: int
    error_message: str | None = None


class OpportunityBase(BaseModel):
    opportunity_source_id: UUID | None = None
    casting_office_id: UUID | None = None
    representation_id: UUID | None = None
    casting_contact_id: UUID | None = None
    source_type: str = "Manual Entry"
    platform: str | None = None
    from_agent: bool = False
    role: str = Field(min_length=1, max_length=255)
    project: str = Field(min_length=1, max_length=255)
    project_type: str | None = None
    role_type: str | None = None
    archetypes: list[str] = []
    union: str = Field(min_length=1, max_length=80)
    rate: str | None = None
    location: str = Field(min_length=1, max_length=255)
    shoot_location: str | None = None
    audition_location: str | None = None
    travel_covered: bool | None = None
    housing_covered: bool | None = None
    description: str = Field(min_length=1)
    original_post_url: str | None = Field(default=None, max_length=1000)
    status: str = "open"
    breakdown_classification: str = "Acting Role"
    rejection_reason: str | None = None
    highlighted_text_as_rejection_reason: str | None = None
    source_metadata: dict = {}
    production_details: dict = {}
    role_details: dict = {}
    extracted_facts: dict = {}
    ai_inference: dict = {}
    ai_summary: str | None = None
    audition_type: str = "Self-Tape"
    audition_travel_hours: float | None = None
    submission_deadline: datetime | None = None
    audition_deadline: datetime | None = None
    callback_date: datetime | None = None
    shoot_start_date: date | None = None
    shoot_end_date: date | None = None
    priority: str = "Medium"


class OpportunityCreate(OpportunityBase):
    pass


class OpportunityUpdate(BaseModel):
    override_reason: str | None = None
    opportunity_source_id: UUID | None = None
    casting_office_id: UUID | None = None
    representation_id: UUID | None = None
    casting_contact_id: UUID | None = None
    source_type: str | None = None
    platform: str | None = None
    from_agent: bool | None = None
    role: str | None = Field(default=None, min_length=1, max_length=255)
    project: str | None = Field(default=None, min_length=1, max_length=255)
    project_type: str | None = None
    role_type: str | None = None
    archetypes: list[str] | None = None
    union: str | None = Field(default=None, min_length=1, max_length=80)
    rate: str | None = None
    location: str | None = Field(default=None, min_length=1, max_length=255)
    shoot_location: str | None = None
    audition_location: str | None = None
    travel_covered: bool | None = None
    housing_covered: bool | None = None
    description: str | None = Field(default=None, min_length=1)
    original_post_url: str | None = Field(default=None, max_length=1000)
    status: str | None = None
    breakdown_classification: str | None = None
    rejection_reason: str | None = None
    highlighted_text_as_rejection_reason: str | None = None
    source_metadata: dict | None = None
    production_details: dict | None = None
    role_details: dict | None = None
    ai_summary: str | None = None
    audition_type: str | None = None
    audition_travel_hours: float | None = None
    submission_deadline: datetime | None = None
    audition_deadline: datetime | None = None
    callback_date: datetime | None = None
    shoot_start_date: date | None = None
    shoot_end_date: date | None = None
    priority: str | None = None


class OpportunityRead(OpportunityBase, TimestampedModel):
    normalized_key: str | None = None
    category: str | None = None
    source_reliability_score: float = 0.7
    is_duplicate: bool = False
    is_demo_data: bool = False
    visibility_status: str = "visible"
    hidden_reason: str | None = None
    hidden_by_rule: str | None = None
    audition_drive_time: float | None = None
    manual_review_required: bool = False
    urgency_score: int = 0
    quality_score: int = 50
    quality_explanation: str | None = None
    confidence_level: str = "Medium"
    risk_level: str = "Medium"
    risk_explanation: str | None = None
    demographic_match_status: str = "Needs Review"
    demographic_match_explanation: str | None = None
    demographic_match_details: dict = {}
    watchlist_match_names: list = []
    watchlist_match_count: int = 0
    watchlist_notification: str | None = None
    already_tracked: bool = False
    tracked_submission_id: UUID | None = None
    breakdown_roles: list[BreakdownRoleRead] = []
    breakdown_sections: list[BreakdownSectionRead] = []
    breakdown_parse_runs: list[BreakdownParseRunRead] = []


class MaterialMatchAsset(BaseModel):
    asset_id: UUID
    asset_name: str
    asset_type: str
    matched_terms: list[str]
    reason: str


class MaterialOpportunityMatch(BaseModel):
    opportunity: OpportunityRead
    score: int
    match_type: str
    matched_assets: list[MaterialMatchAsset]
    matched_terms: list[str]
    missing_material_types: list[str]
    explanation: str


class BreakdownTextParse(BaseModel):
    raw_text: str = Field(min_length=10)


class OpportunityReject(BaseModel):
    highlighted_text_as_rejection_reason: str | None = None
    rejection_reason: str | None = None
