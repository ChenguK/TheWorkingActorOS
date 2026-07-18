from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DiscoverySourcePlugin(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "discovery_source_plugins"

    name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    priority_rank: Mapped[int] = mapped_column(nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    implementation_key: Mapped[str] = mapped_column(String(120), nullable=False)
    reliability_score: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)


class DiscoveryProviderSettings(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "discovery_provider_settings"

    provider_key: Mapped[str] = mapped_column(String(160), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(180), nullable=False)
    tier: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(120), nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    poll_frequency_minutes: Mapped[int] = mapped_column(Integer, default=1440, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    authentication_method: Mapped[str] = mapped_column(String(120), default="None", nullable=False)
    supported_authentication_methods: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    reliability_score: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    health_status: Mapped[str] = mapped_column(String(80), default="unknown", nullable=False)
    health_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_health_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("tier >= 1 AND tier <= 5", name="ck_discovery_provider_settings_tier"),
        CheckConstraint("poll_frequency_minutes >= 0", name="ck_discovery_provider_settings_poll_frequency"),
        CheckConstraint("priority >= 0", name="ck_discovery_provider_settings_priority"),
        CheckConstraint(
            "reliability_score >= 0 AND reliability_score <= 1",
            name="ck_discovery_provider_settings_reliability",
        ),
    )


class DiscoverySettings(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "discovery_settings"

    film_tv_breakdown_limit: Mapped[int] = mapped_column(Integer, default=25, nullable=False)
    theater_breakdown_limit: Mapped[int] = mapped_column(Integer, default=25, nullable=False)
    commercial_breakdown_limit: Mapped[int] = mapped_column(Integer, default=25, nullable=False)
    voiceover_breakdown_limit: Mapped[int] = mapped_column(Integer, default=25, nullable=False)

    __table_args__ = (
        CheckConstraint("film_tv_breakdown_limit >= 0", name="ck_discovery_settings_film_tv_limit"),
        CheckConstraint("theater_breakdown_limit >= 0", name="ck_discovery_settings_theater_limit"),
        CheckConstraint("commercial_breakdown_limit >= 0", name="ck_discovery_settings_commercial_limit"),
        CheckConstraint("voiceover_breakdown_limit >= 0", name="ck_discovery_settings_voiceover_limit"),
    )


class SourceResearchItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "source_research_items"

    name: Mapped[str] = mapped_column(String(180), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    base_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    suggested_specific_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    approved_discovery_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="Suggested", nullable=False)
    reliability_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_researched_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_checked_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_by_ai: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    approved_by_user: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejected_by_user: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    previous_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    provider_key: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    added_to_discovery_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_health: Mapped[str] = mapped_column(String(80), default="Unchecked", nullable=False)
    suggested_classification: Mapped[str] = mapped_column(String(80), default="Needs Review", nullable=False)
    health_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    redirect_target: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    visible_text_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    organization_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    submitted_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    final_resolved_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    url_health_status: Mapped[str] = mapped_column(String(80), default="Unchecked", nullable=False)
    organization_legitimacy: Mapped[str] = mapped_column(String(80), default="Unverified Organization", nullable=False)
    source_usefulness: Mapped[str] = mapped_column(String(80), default="Needs Review", nullable=False)
    source_classification: Mapped[str] = mapped_column(String(80), default="Needs Review", nullable=False)
    verification_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    discovered_from_breakdown_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True, index=True
    )
    discovery_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_role_match_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    discovered_from_breakdown = relationship("Opportunity")

    __table_args__ = (
        CheckConstraint(
            "category IN ('Public casting site', 'Casting office', 'Film commission', "
            "'Social media account', 'Production company', 'Theater company', 'Talent platform', 'Other')",
            name="ck_source_research_items_category",
        ),
        CheckConstraint(
            "status IN ('Suggested', 'Researching', 'Approved', 'Rejected', 'Active', 'Paused', 'Deleted')",
            name="ck_source_research_items_status",
        ),
        CheckConstraint(
            "user_rating IS NULL OR (user_rating >= 1 AND user_rating <= 5)",
            name="ck_source_research_items_user_rating",
        ),
        CheckConstraint(
            "source_health IN ('Unchecked', 'Active', 'Dead / Unavailable Domain', 'Placeholder Website', 'No Meaningful Content', 'Blocked', 'Needs Review')",
            name="ck_source_research_items_source_health",
        ),
        CheckConstraint(
            "suggested_classification IN ('Valid Breakdown Source', 'Casting Office', 'Production Company', 'Regional Resource', 'Watch List Source', 'Rejected', 'Not Useful', 'Relationship Source', 'Needs Review')",
            name="ck_source_research_items_suggested_classification",
        ),
    )


class DiscoveryRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "discovery_runs"

    source_plugin_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("discovery_source_plugins.id", ondelete="SET NULL"), nullable=True
    )
    discovery_mode: Mapped[str] = mapped_column(String(40), default="All", nullable=False)
    status: Mapped[str] = mapped_column(String(60), default="queued", nullable=False)
    opportunities_found: Mapped[int] = mapped_column(default=0, nullable=False)
    opportunities_created: Mapped[int] = mapped_column(default=0, nullable=False)
    opportunities_hidden: Mapped[int] = mapped_column(default=0, nullable=False)
    total_found: Mapped[int] = mapped_column(default=0, nullable=False)
    total_saved: Mapped[int] = mapped_column(default=0, nullable=False)
    total_rejected: Mapped[int] = mapped_column(default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    run_payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    source_plugin = relationship("DiscoverySourcePlugin")

    __table_args__ = (
        CheckConstraint("discovery_mode IN ('Theater', 'FilmTV', 'All')", name="ck_discovery_runs_discovery_mode"),
    )


class SubmissionAutomationQueue(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "submission_automation_queue"

    submission_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=True
    )
    opportunity_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False
    )
    recommendation_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_recommendations.id", ondelete="SET NULL"), nullable=True
    )
    adapter_key: Mapped[str] = mapped_column(String(120), nullable=False)
    submission_mode: Mapped[str] = mapped_column(String(80), nullable=False)
    approval_status: Mapped[str] = mapped_column(String(60), default="Pending Approval", nullable=False)
    automation_status: Mapped[str] = mapped_column(String(60), default="Prepared", nullable=False)
    retry_count: Mapped[int] = mapped_column(default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(default=3, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    prepared_payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    execution_log: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    submission = relationship("Submission")
    opportunity = relationship("Opportunity")
    recommendation = relationship("AgentRecommendation")
