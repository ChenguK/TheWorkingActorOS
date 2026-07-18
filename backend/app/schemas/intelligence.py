from datetime import date as date_type
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import TimestampedModel


class ArchetypePerformanceRead(BaseModel):
    archetype: str
    submissions: int
    requested: int
    self_tape_callbacks: int
    in_person_callbacks: int
    pinned: int
    booked: int
    passed: int
    no_response: int
    callback_rate: float
    booking_rate: float


class ArchetypePerformanceDashboardRead(BaseModel):
    metrics: list[ArchetypePerformanceRead]
    best_performing_archetypes: list[str]
    underused_archetypes: list[str]
    overused_archetypes: list[str]
    high_potential_stretch_archetypes: list[str]


class CastingOfficeBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    source_platform: str | None = None
    project_history: list = []
    submission_history: list = []
    callback_history: list = []
    booking_history: list = []
    notes: str | None = None


class CastingOfficeCreate(CastingOfficeBase):
    pass


class CastingOfficeRead(CastingOfficeBase, TimestampedModel):
    pass


class CastingContactBase(BaseModel):
    casting_office_id: UUID
    name: str = Field(min_length=1, max_length=255)
    role: str = "Casting Director"
    email: str | None = None
    notes: str | None = None


class CastingContactCreate(CastingContactBase):
    pass


class CastingContactRead(CastingContactBase, TimestampedModel):
    pass


class CastingOfficeAnalyticsRead(BaseModel):
    casting_office_id: UUID | None = None
    casting_office: str
    submissions: int
    callbacks: int
    bookings: int
    callback_rate: float
    booking_rate: float
    best_materials: list[str]
    stretch_response_signal: str


class RoleSimilarityRead(BaseModel):
    source_role: str
    similar_roles: list[dict]
    explanation: str


class AuditionPreparationBriefRead(TimestampedModel):
    opportunity_id: UUID
    submission_id: UUID | None = None
    brief: dict
    explanation: str


class MaterialCreationPlanCreate(BaseModel):
    missing_asset: str
    target_archetype: str | None = None
    career_task_id: UUID | None = None


class MaterialCreationPlanRead(TimestampedModel):
    career_task_id: UUID | None = None
    missing_asset: str
    target_archetype: str | None = None
    plan_status: str
    plan: dict
    explanation: str


class MaterialCreationPlanUpdate(BaseModel):
    plan_status: str | None = None


class ScriptSourceBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    url: str | None = Field(default=None, max_length=500)
    source_type: str = Field(min_length=1, max_length=120)
    rights_status: str = "Unknown"
    notes: str | None = None
    approved: bool = False


class ScriptSourceCreate(ScriptSourceBase):
    pass


class ScriptSourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    url: str | None = Field(default=None, max_length=500)
    source_type: str | None = Field(default=None, min_length=1, max_length=120)
    rights_status: str | None = None
    notes: str | None = None
    approved: bool | None = None


class ScriptSourceRead(ScriptSourceBase, TimestampedModel):
    pass


class SceneCandidateFindRequest(BaseModel):
    career_task_id: UUID | None = None
    material_plan_id: UUID | None = None
    target_archetype: str | None = None
    material_goal: str | None = None
    generate_original_only: bool = False


class SceneCandidateUpdate(BaseModel):
    action_status: str | None = None
    notes: str | None = None


class SceneCandidateRead(TimestampedModel):
    script_source_id: UUID | None = None
    career_task_id: UUID | None = None
    title: str
    result_type: str
    rights_status: str
    source_url: str | None = None
    logline: str
    scene_brief: dict
    action_status: str
    notes: str | None = None


class CareerPathSimulationCreate(BaseModel):
    goal: str = Field(min_length=1)


class CareerPathSimulationRead(TimestampedModel):
    actor_profile_id: UUID
    goal: str
    result: dict
    explanation: str


class IntelligenceDashboardRead(BaseModel):
    archetype_performance: ArchetypePerformanceDashboardRead
    casting_office_analytics: list[CastingOfficeAnalyticsRead]
    role_similarity: list[RoleSimilarityRead]


RelationshipRole = str
RelationshipStrength = str


class ActorRelationshipBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    role_title: RelationshipRole
    company_office: str | None = Field(default=None, max_length=255)
    projects: list[str] = []
    notes: str | None = None
    last_contact_date: date_type | None = None
    relationship_strength: RelationshipStrength = "Warm"
    linked_outcomes: list[str] = []


class ActorRelationshipCreate(ActorRelationshipBase):
    linked_opportunity_ids: list[UUID] = []
    linked_submission_ids: list[UUID] = []


class ActorRelationshipUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    role_title: RelationshipRole | None = None
    company_office: str | None = Field(default=None, max_length=255)
    projects: list[str] | None = None
    notes: str | None = None
    last_contact_date: date_type | None = None
    relationship_strength: RelationshipStrength | None = None
    linked_outcomes: list[str] | None = None
    linked_opportunity_ids: list[UUID] | None = None
    linked_submission_ids: list[UUID] | None = None


class ActorRelationshipRead(ActorRelationshipBase, TimestampedModel):
    linked_opportunity_ids: list[UUID] = []
    linked_submission_ids: list[UUID] = []


class RelationshipAnalyticsRow(BaseModel):
    relationship_id: UUID
    name: str
    role_title: str
    company_office: str | None = None
    relationship_strength: str
    submissions: int
    callbacks: int
    pins: int
    bookings: int
    repeat_opportunities: int
    callback_rate: float
    booking_rate: float
    correlation_signal: str


class RelationshipAnalyticsRead(BaseModel):
    rows: list[RelationshipAnalyticsRow]
    strongest_relationships: list[str]
    relationship_agent_explanation: str


class SelfTapeBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    role_type: str | None = Field(default=None, max_length=120)
    archetypes: list[str] = []
    file_path: str = Field(min_length=1)
    linked_opportunity_id: UUID | None = None
    linked_submission_id: UUID | None = None
    outcome: str | None = Field(default=None, max_length=80)
    notes: str | None = None
    date_created: date_type


class SelfTapeCreate(SelfTapeBase):
    pass


class SelfTapeUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    role_type: str | None = Field(default=None, max_length=120)
    archetypes: list[str] | None = None
    file_path: str | None = Field(default=None, min_length=1)
    linked_opportunity_id: UUID | None = None
    linked_submission_id: UUID | None = None
    outcome: str | None = Field(default=None, max_length=80)
    notes: str | None = None
    date_created: date_type | None = None


class SelfTapeRead(SelfTapeBase, TimestampedModel):
    pass


class SelfTapeAnalyticsRead(BaseModel):
    by_archetype: list[dict]
    by_outcome: list[dict]
    best_performing_tapes: list[SelfTapeRead]
    underused_tapes: list[SelfTapeRead]


class AuditionJournalEntryBase(BaseModel):
    submission_id: UUID | None = None
    opportunity_id: UUID | None = None
    date: date_type
    preparation_notes: str | None = None
    performance_notes: str | None = None
    casting_notes: str | None = None
    wardrobe_notes: str | None = None
    emotional_notes: str | None = None
    follow_up_notes: str | None = None


class AuditionJournalEntryCreate(AuditionJournalEntryBase):
    pass


class AuditionJournalEntryUpdate(BaseModel):
    submission_id: UUID | None = None
    opportunity_id: UUID | None = None
    date: date_type | None = None
    preparation_notes: str | None = None
    performance_notes: str | None = None
    casting_notes: str | None = None
    wardrobe_notes: str | None = None
    emotional_notes: str | None = None
    follow_up_notes: str | None = None


class AuditionJournalEntryRead(AuditionJournalEntryBase, TimestampedModel):
    pass


class CallbackEventBase(BaseModel):
    submission_id: UUID | None = None
    opportunity_id: UUID | None = None
    event_name: str = Field(min_length=1, max_length=120)
    event_type: str = "First Callback"
    event_datetime: date_type | None = None
    location: str | None = None
    is_virtual: bool = False
    preparation_notes: str | None = None
    outcome: str | None = None
    notes: str | None = None


class CallbackEventCreate(CallbackEventBase):
    pass


class CallbackEventUpdate(BaseModel):
    submission_id: UUID | None = None
    opportunity_id: UUID | None = None
    event_name: str | None = Field(default=None, min_length=1, max_length=120)
    event_type: str | None = None
    event_datetime: date_type | None = None
    location: str | None = None
    is_virtual: bool | None = None
    preparation_notes: str | None = None
    outcome: str | None = None
    notes: str | None = None


class CallbackEventRead(CallbackEventBase, TimestampedModel):
    pass


class CommunicationLogBase(BaseModel):
    representation_id: UUID | None = None
    opportunity_id: UUID | None = None
    submission_id: UUID | None = None
    date: date_type
    topic: str = Field(min_length=1, max_length=255)
    notes: str | None = None
    follow_up_needed: bool = False
    follow_up_date: date_type | None = None


class CommunicationLogCreate(CommunicationLogBase):
    pass


class CommunicationLogUpdate(BaseModel):
    representation_id: UUID | None = None
    opportunity_id: UUID | None = None
    submission_id: UUID | None = None
    date: date_type | None = None
    topic: str | None = Field(default=None, min_length=1, max_length=255)
    notes: str | None = None
    follow_up_needed: bool | None = None
    follow_up_date: date_type | None = None


class CommunicationLogRead(CommunicationLogBase, TimestampedModel):
    pass


class AuditionReadinessRead(BaseModel):
    opportunity_id: UUID
    opportunity_label: str
    readiness_label: str
    readiness_percentage: int
    score_breakdown: dict[str, int]
    missing_materials: list[str]
    character_archetypes: list[str] = []
    character_parsing_confidence: int = 0
    character_parsing_status: str
    debug_score_available: bool = True
    explanation: str


class IndustryTrendInsightRead(BaseModel):
    trend_type: str
    label: str
    count: int
    insight: str
    recommended_action: str | None = None


class IndustryTrendDashboardRead(BaseModel):
    role_type: list[IndustryTrendInsightRead]
    archetype: list[IndustryTrendInsightRead]
    project_type: list[IndustryTrendInsightRead]
    union_status: list[IndustryTrendInsightRead]
    location: list[IndustryTrendInsightRead]
    audition_type: list[IndustryTrendInsightRead]
    submission_source: list[IndustryTrendInsightRead]
    submitted_project_type: list[IndustryTrendInsightRead] = []
    callback_archetype: list[IndustryTrendInsightRead] = []
    booking_archetype: list[IndustryTrendInsightRead] = []
    insights: list[str]
    pattern_stage: str = "Add Data First"
    stage: str = "Add Data First"
    tracked_breakdowns_or_auditions: int = 0
    submission_count: int = 0
    outcome_count: int = 0
    unlock_message: str = "Add or track a few more auditions to unlock casting pattern insights."


class QuarterlyCareerReviewCreate(BaseModel):
    year: int = Field(ge=2000, le=2100)
    quarter: int = Field(ge=1, le=4)


class QuarterlyCareerReviewRead(TimestampedModel):
    actor_profile_id: UUID
    year: int
    quarter: int
    report: dict
    explanation: str


class DreamRoleTargetBase(BaseModel):
    target_type: str
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    target_archetypes: list[str] = []
    target_genres: list[str] = []
    target_offices: list[str] = []
    notes: str | None = None


class DreamRoleTargetCreate(DreamRoleTargetBase):
    pass


class DreamRoleTargetUpdate(BaseModel):
    target_type: str | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    target_archetypes: list[str] | None = None
    target_genres: list[str] | None = None
    target_offices: list[str] | None = None
    notes: str | None = None


class DreamRoleTargetRead(DreamRoleTargetBase, TimestampedModel):
    actor_profile_id: UUID


class DreamRoleReadinessRead(BaseModel):
    target: DreamRoleTargetRead
    current_readiness_score: int
    missing_materials: list[str]
    recommended_actions: list[str]
    related_career_development_tasks: list[dict]
    explanation: str
