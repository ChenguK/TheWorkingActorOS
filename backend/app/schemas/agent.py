from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import TimestampedModel


class AgentRecommendationRead(TimestampedModel):
    opportunity_id: UUID
    actor_profile_id: UUID
    agent_version: str
    score: int
    match_type: str
    display_opportunity: bool
    explanation: str
    score_breakdown: dict
    audition_type: str
    audition_travel_hours: float | None = None
    audition_decision: str
    audition_explanation: str
    travel_explanation: str
    archetype_explanation: str
    asset_explanation: str
    submission_strategy_explanation: str
    confidence_level: str = "Medium"
    risk_level: str = "Medium"
    risk_explanation: str | None = None
    recommended_headshot_id: UUID | None = None
    recommended_reel_id: UUID | None = None
    recommended_resume_id: UUID | None = None
    recommended_slate_id: UUID | None = None
    recommended_note: str


class RecommendationExplanation(BaseModel):
    score: int
    match_type: str
    score_breakdown: dict
    audition_type: str
    audition_travel_hours: float | None
    audition_decision: str
    audition_explanation: str
    travel_explanation: str
    archetype_explanation: str
    asset_explanation: str
    submission_strategy_explanation: str
    confidence_level: str
    risk_level: str
    risk_explanation: str | None = None
    explanation: str


class RecommendedMaterialSubmissionCreate(BaseModel):
    asset_ids: list[UUID] | None = None
    current_status: str = "Requested"
    notes: str | None = None


class RecommendationFeedbackCreate(BaseModel):
    feedback_type: str = Field(pattern="^(This Fits Me|Not My Type|Interesting Stretch|Save For Later)$")
    fit_reasons: list[str] = []
    notes: str | None = None


class RecommendationFeedbackRead(TimestampedModel):
    actor_profile_id: UUID
    opportunity_id: UUID
    recommendation_id: UUID | None = None
    feedback_type: str
    fit_reasons: list
    notes: str | None = None


class ExecutivePriorityRead(BaseModel):
    rank: int
    title: str
    reason: str
    category: str
    action_label: str
    target_path: str
    urgency: int


class LearningInsightRead(TimestampedModel):
    actor_profile_id: UUID
    trends: dict
    recommendation_weights: dict
    explanation: str


class CareerMemoryBase(BaseModel):
    actor_profile_id: UUID | None = None
    current_career_goals: list[str] = []
    current_focus: str | None = None
    stretch_archetypes: list[str] = []
    preferred_project_types: list[str] = []
    preferred_markets: list[str] = []
    unavailable_dates: list[str] = []
    career_notes: str | None = None
    executive_notes: str | None = None


class CareerMemoryUpdate(CareerMemoryBase):
    pass


class CareerMemoryRead(CareerMemoryBase, TimestampedModel):
    pass


class ExecutiveBriefRead(TimestampedModel):
    actor_profile_id: UUID | None = None
    period_start: date
    period_end: date
    brief_type: str
    new_matching_breakdowns: list
    submissions_completed: list
    callbacks_received: list
    bookings: list
    materials_used: list
    career_progress: list
    recommended_priorities: list
    summary: str


class CareerRecommendationRead(TimestampedModel):
    actor_profile_id: UUID
    strengths: list
    growth_opportunities: list
    archetypes_to_expand: list
    recommended_headshots: list
    recommended_role_types: list
    strong_match_roles: list
    growth_match_roles: list
    stretch_roles: list
    explanation: str


class CareerSwotAnalysisRead(TimestampedModel):
    actor_profile_id: UUID
    strengths: list
    weaknesses: list
    opportunities: list
    threats: list
    explanation: str


class CareerTaskRead(TimestampedModel):
    career_recommendation_id: UUID | None = None
    title: str
    description: str
    priority: str
    estimated_impact: str
    related_archetype: str
    target_roles: list
    status: str


class CareerDevelopmentTaskBase(BaseModel):
    title: str
    description: str
    priority: str = "Medium"
    status: str = "Not Started"
    related_archetype: str | None = None
    target_role_types: list[str] = []
    estimated_impact: str = "Medium"
    reason: str | None = None
    supported_archetypes: list[str] = []
    created_by_agent: bool = False
    archetype_id: UUID | None = None
    asset_id: UUID | None = None
    career_recommendation_id: UUID | None = None


class CareerDevelopmentTaskCreate(CareerDevelopmentTaskBase):
    pass


class CareerDevelopmentTaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: str | None = None
    status: str | None = None
    related_archetype: str | None = None
    target_role_types: list[str] | None = None
    estimated_impact: str | None = None
    reason: str | None = None
    supported_archetypes: list[str] | None = None
    created_by_agent: bool | None = None
    archetype_id: UUID | None = None
    asset_id: UUID | None = None
    career_recommendation_id: UUID | None = None


class CareerDevelopmentTaskRead(CareerDevelopmentTaskBase, TimestampedModel):
    completed_at: datetime | None = None


class CastingGoalBase(BaseModel):
    actor_profile_id: UUID | None = None
    title: str
    goal_type: str = "TV"
    target_archetypes: list[str] = []
    target_role_types: list[str] = []
    target_project_types: list[str] = []
    target_markets: list[str] = []
    target_casting_offices: list[str] = []
    target_deadline: date | None = None
    priority: str = "Medium"
    status: str = "Active"
    notes: str | None = None


class CastingGoalCreate(CastingGoalBase):
    pass


class CastingGoalUpdate(BaseModel):
    title: str | None = None
    goal_type: str | None = None
    target_archetypes: list[str] | None = None
    target_role_types: list[str] | None = None
    target_project_types: list[str] | None = None
    target_markets: list[str] | None = None
    target_casting_offices: list[str] | None = None
    target_deadline: date | None = None
    priority: str | None = None
    status: str | None = None
    notes: str | None = None


class CastingGoalRead(CastingGoalBase, TimestampedModel):
    pass


class WatchListBase(BaseModel):
    actor_profile_id: UUID | None = None
    title: str
    category: str
    terms: list[str] = []
    enabled: bool = True
    priority: str = "Medium"
    notes: str | None = None


class WatchListCreate(WatchListBase):
    pass


class WatchListUpdate(BaseModel):
    title: str | None = None
    category: str | None = None
    terms: list[str] | None = None
    enabled: bool | None = None
    priority: str | None = None
    notes: str | None = None


class WatchListRead(WatchListBase, TimestampedModel):
    match_count: int = 0
    last_matched_at: datetime | None = None


class DiscoveryPluginRead(BaseModel):
    name: str
    priority_rank: int
    source_type: str
    implementation_key: str
    reliability_score: float
    category: str = "Public Casting Sites"
    tier: int = 2
    enabled: bool = False


class SubmissionAutomationQueueRead(TimestampedModel):
    submission_id: UUID | None = None
    opportunity_id: UUID
    recommendation_id: UUID | None = None
    adapter_key: str
    submission_mode: str
    approval_status: str
    automation_status: str
    retry_count: int
    max_retries: int
    error_message: str | None = None
    prepared_payload: dict
    execution_log: list
    approved_at: datetime | None = None
    executed_at: datetime | None = None


class SelfTapeWorkflowBase(BaseModel):
    opportunity_id: UUID
    submission_id: UUID | None = None
    status: str = "Not Started"
    sides_file_path: str | None = None
    reader_needed: bool = False
    tape_due_at: datetime | None = None
    slate_requirements: str | None = None
    wardrobe_notes: str | None = None
    upload_link: str | None = None
    final_file_path: str | None = None


class SelfTapeWorkflowCreate(SelfTapeWorkflowBase):
    pass


class SelfTapeWorkflowUpdate(BaseModel):
    opportunity_id: UUID | None = None
    submission_id: UUID | None = None
    status: str | None = None
    sides_file_path: str | None = None
    reader_needed: bool | None = None
    tape_due_at: datetime | None = None
    slate_requirements: str | None = None
    wardrobe_notes: str | None = None
    upload_link: str | None = None
    final_file_path: str | None = None


class SelfTapeWorkflowRead(SelfTapeWorkflowBase, TimestampedModel):
    pass


class OutcomeNudgeRead(TimestampedModel):
    submission_id: UUID
    nudge_type: str
    message: str
    status: str
    due_at: datetime | None = None
    resolved_at: datetime | None = None


class MaterialGapAlertRead(TimestampedModel):
    actor_profile_id: UUID
    archetype: str
    gap_type: str
    message: str
    priority: str
    status: str
    recommended_action: str
    created_by_agent: bool


class AssetPerformanceRead(BaseModel):
    asset_id: UUID
    asset_name: str
    asset_type: str
    submissions: int
    positive_outcomes: int
    callback_rate: float


class CommandCenterIntelligenceContributorRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(max_length=120)
    points: int
    explanation: str | None = Field(default=None, max_length=240)


class CommandCenterIntelligenceConfidenceRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: Literal["High", "Medium", "Low", "Not Scored"]
    summary: str = Field(max_length=160)


class CommandCenterIntelligenceSummaryRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal[1]
    overall_score: int = Field(ge=0, le=100)
    action: Literal[
        "ignore",
        "save_for_later",
        "good_stretch_role",
        "apply_now",
        "review_today",
        "low_priority",
    ]
    action_label: Literal[
        "Ignore",
        "Save for Later",
        "Good Stretch Role",
        "Apply Now",
        "Review Today",
        "Low Priority",
    ]
    action_reason_code: Literal[
        "hard_override",
        "duplicate_opportunity",
        "already_tracked",
        "strategic_stretch",
        "high_priority_actionable",
        "strong_score_review",
        "urgent_deadline_review",
        "promising_not_urgent",
        "limited_current_value",
    ]
    confidence: CommandCenterIntelligenceConfidenceRead
    hard_override: bool
    hard_override_reason: Literal[
        "user_rejected",
        "expired",
        "rejected_classification",
        "profile_incompatibility",
        "availability_conflict",
        "travel_limit",
        "discarded",
    ] | None = None
    top_positive_contributors: list[CommandCenterIntelligenceContributorRead] = Field(
        max_length=3
    )
    top_negative_contributors: list[CommandCenterIntelligenceContributorRead] = Field(
        max_length=3
    )


class CommandCenterOpportunityCardRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    role: str
    project: str
    original_post_url: str | None
    priority: str
    urgency_score: int
    quality_score: int
    confidence_level: str
    risk_level: str
    intelligence: CommandCenterIntelligenceSummaryRead | None = None


class ActorCommandCenterRead(BaseModel):
    today_opportunities: list[CommandCenterOpportunityCardRead]
    executive_priorities: list[dict]
    chief_of_staff_priorities: list[dict] = []
    since_last_visit: list[dict] = []
    upcoming_attention: list[dict] = []
    today_career_recommendation: dict | None = None
    platform_check_ins: list[dict] = []
    queued_submissions: list[dict]
    upcoming_deadlines: list[dict]
    outcome_nudges: list[dict]
    career_tasks: list[dict]
    material_gaps: list[dict]
    asset_performance: list[AssetPerformanceRead]
