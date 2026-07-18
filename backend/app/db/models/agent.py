from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AgentRecommendation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_recommendations"

    opportunity_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False
    )
    actor_profile_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("actor_profiles.id", ondelete="CASCADE"), nullable=False
    )
    agent_version: Mapped[str] = mapped_column(String(60), default="strategy-v1", nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    match_type: Mapped[str] = mapped_column(String(80), nullable=False)
    display_opportunity: Mapped[bool] = mapped_column(default=True, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    score_breakdown: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    audition_type: Mapped[str] = mapped_column(String(40), nullable=False)
    audition_travel_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    audition_decision: Mapped[str] = mapped_column(String(80), nullable=False)
    audition_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    travel_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    archetype_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    asset_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    submission_strategy_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_level: Mapped[str] = mapped_column(String(40), default="Medium", nullable=False)
    risk_level: Mapped[str] = mapped_column(String(40), default="Medium", nullable=False)
    risk_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_headshot_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    recommended_reel_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    recommended_resume_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    recommended_slate_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    recommended_note: Mapped[str] = mapped_column(Text, nullable=False)

    opportunity = relationship("Opportunity", back_populates="recommendations")
    actor_profile = relationship("ActorProfile")
    recommended_headshot = relationship("Asset", foreign_keys=[recommended_headshot_id])
    recommended_reel = relationship("Asset", foreign_keys=[recommended_reel_id])
    recommended_resume = relationship("Asset", foreign_keys=[recommended_resume_id])
    recommended_slate = relationship("Asset", foreign_keys=[recommended_slate_id])


class RecommendationFeedback(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recommendation_feedback"

    actor_profile_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("actor_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    opportunity_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recommendation_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_recommendations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    feedback_type: Mapped[str] = mapped_column(String(80), nullable=False)
    fit_reasons: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    actor_profile = relationship("ActorProfile")
    opportunity = relationship("Opportunity")
    recommendation = relationship("AgentRecommendation")


class LearningInsight(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "learning_insights"

    actor_profile_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("actor_profiles.id", ondelete="CASCADE"), nullable=False
    )
    trends: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    recommendation_weights: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)


class CareerMemory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "career_memories"

    actor_profile_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("actor_profiles.id", ondelete="CASCADE"), nullable=True, index=True
    )
    current_career_goals: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    current_focus: Mapped[str | None] = mapped_column(Text, nullable=True)
    stretch_archetypes: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    preferred_project_types: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    preferred_markets: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    unavailable_dates: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    career_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    executive_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    actor_profile = relationship("ActorProfile")


class ExecutiveBrief(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "executive_briefs"

    actor_profile_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("actor_profiles.id", ondelete="CASCADE"), nullable=True, index=True
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    brief_type: Mapped[str] = mapped_column(String(40), nullable=False, default="Weekly")
    new_matching_breakdowns: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    submissions_completed: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    callbacks_received: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    bookings: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    materials_used: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    career_progress: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    recommended_priorities: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)

    actor_profile = relationship("ActorProfile")


class ChiefOfStaffState(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "chief_of_staff_states"

    actor_profile_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("actor_profiles.id", ondelete="CASCADE"), nullable=True, index=True
    )
    last_dashboard_visit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    actor_profile = relationship("ActorProfile")


class CareerRecommendation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "career_recommendations"

    actor_profile_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("actor_profiles.id", ondelete="CASCADE"), nullable=False
    )
    strengths: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    growth_opportunities: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    archetypes_to_expand: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    recommended_headshots: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    recommended_role_types: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    strong_match_roles: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    growth_match_roles: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    stretch_roles: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)


class CareerSwotAnalysis(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "career_swot_analyses"

    actor_profile_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("actor_profiles.id", ondelete="CASCADE"), nullable=False
    )
    strengths: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    weaknesses: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    opportunities: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    threats: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    actor_profile = relationship("ActorProfile")


class CareerTask(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "career_tasks"

    career_recommendation_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("career_recommendations.id", ondelete="CASCADE"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(40), nullable=False)
    estimated_impact: Mapped[str] = mapped_column(String(40), nullable=False)
    related_archetype: Mapped[str] = mapped_column(String(120), nullable=False)
    target_roles: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="open", nullable=False)


class CareerDevelopmentTask(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "career_development_tasks"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(40), nullable=False, default="Medium")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="Not Started")
    related_archetype: Mapped[str | None] = mapped_column(String(120), nullable=True)
    target_role_types: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    estimated_impact: Mapped[str] = mapped_column(String(40), nullable=False, default="Medium")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    supported_archetypes: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    created_by_agent: Mapped[bool] = mapped_column(default=False, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archetype_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("archetypes.id", ondelete="SET NULL"), nullable=True
    )
    asset_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    career_recommendation_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("career_recommendations.id", ondelete="SET NULL"), nullable=True
    )

    archetype = relationship("Archetype")
    asset = relationship("Asset")
    career_recommendation = relationship("CareerRecommendation")


class WatchList(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "watch_lists"

    actor_profile_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("actor_profiles.id", ondelete="CASCADE"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(120), nullable=False)
    terms: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    priority: Mapped[str] = mapped_column(String(40), nullable=False, default="Medium")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    match_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_matched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    actor_profile = relationship("ActorProfile")


class CastingGoal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "casting_goals"

    actor_profile_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("actor_profiles.id", ondelete="CASCADE"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    goal_type: Mapped[str] = mapped_column(String(80), nullable=False)
    target_archetypes: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    target_role_types: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    target_project_types: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    target_markets: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    target_casting_offices: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    target_deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    priority: Mapped[str] = mapped_column(String(40), nullable=False, default="Medium")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="Active")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    actor_profile = relationship("ActorProfile")


class SelfTapeWorkflow(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "self_tape_workflows"

    opportunity_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False
    )
    submission_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("submissions.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(40), default="Not Started", nullable=False)
    sides_file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reader_needed: Mapped[bool] = mapped_column(default=False, nullable=False)
    tape_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    slate_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    wardrobe_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    upload_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    final_file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    opportunity = relationship("Opportunity")
    submission = relationship("Submission")


class OutcomeNudge(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "outcome_nudges"

    submission_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False
    )
    nudge_type: Mapped[str] = mapped_column(String(80), nullable=False, default="Follow Up")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="Open", nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    submission = relationship("Submission")


class MaterialGapAlert(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "material_gap_alerts"

    actor_profile_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("actor_profiles.id", ondelete="CASCADE"), nullable=False
    )
    archetype: Mapped[str] = mapped_column(String(120), nullable=False)
    gap_type: Mapped[str] = mapped_column(String(80), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(40), default="Medium", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="Open", nullable=False)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_agent: Mapped[bool] = mapped_column(default=True, nullable=False)

    actor_profile = relationship("ActorProfile")
