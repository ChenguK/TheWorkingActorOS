from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class OpportunitySource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "opportunity_sources"

    name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False, default="manual")
    priority_rank: Mapped[int] = mapped_column(nullable=False, default=1)
    is_enabled: Mapped[bool] = mapped_column(nullable=False, default=True)

    opportunities = relationship("Opportunity", back_populates="source")


class Opportunity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "opportunities"

    opportunity_source_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunity_sources.id", ondelete="SET NULL"), nullable=True
    )
    casting_office_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("casting_offices.id", ondelete="SET NULL"), nullable=True
    )
    representation_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("representations.id", ondelete="SET NULL"), nullable=True
    )
    casting_contact_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("casting_contacts.id", ondelete="SET NULL"), nullable=True
    )
    source_type: Mapped[str] = mapped_column(String(80), default="Manual Entry", nullable=False)
    platform: Mapped[str | None] = mapped_column(String(120), nullable=True)
    from_agent: Mapped[bool] = mapped_column(default=False, nullable=False)
    role: Mapped[str] = mapped_column(String(255), nullable=False)
    project: Mapped[str] = mapped_column(String(255), nullable=False)
    project_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    role_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    archetypes: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    union: Mapped[str] = mapped_column(String(80), nullable=False)
    rate: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    shoot_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    audition_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    travel_covered: Mapped[bool | None] = mapped_column(nullable=True)
    housing_covered: Mapped[bool | None] = mapped_column(nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    original_post_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(60), nullable=False, default="open")
    normalized_key: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_reliability_score: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    is_duplicate: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_demo_data: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)
    breakdown_classification: Mapped[str] = mapped_column(String(80), default="Unknown", nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    highlighted_text_as_rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    audition_type: Mapped[str] = mapped_column(String(40), default="Self-Tape", nullable=False)
    audition_travel_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    visibility_status: Mapped[str] = mapped_column(String(40), default="visible", nullable=False)
    hidden_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    hidden_by_rule: Mapped[str | None] = mapped_column(String(120), nullable=True)
    audition_drive_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    manual_review_required: Mapped[bool] = mapped_column(default=False, nullable=False)
    submission_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    audition_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    callback_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    shoot_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    shoot_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    priority: Mapped[str] = mapped_column(String(40), default="Medium", nullable=False)
    urgency_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quality_score: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    quality_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_level: Mapped[str] = mapped_column(String(40), default="Medium", nullable=False)
    risk_level: Mapped[str] = mapped_column(String(40), default="Medium", nullable=False)
    risk_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    demographic_match_status: Mapped[str] = mapped_column(String(40), default="Needs Review", nullable=False)
    demographic_match_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    demographic_match_details: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    watchlist_match_names: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    watchlist_match_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    watchlist_notification: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    production_details: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    role_details: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    extracted_facts: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    ai_inference: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    source = relationship("OpportunitySource", back_populates="opportunities")
    casting_office = relationship("CastingOffice", back_populates="opportunities")
    representation = relationship("Representation")
    casting_contact = relationship("CastingContact")
    submissions = relationship("Submission", back_populates="opportunity", passive_deletes=True)
    recommendations = relationship(
        "AgentRecommendation", back_populates="opportunity", cascade="all, delete-orphan"
    )
    breakdown_roles = relationship(
        "BreakdownRole",
        back_populates="breakdown",
        cascade="all, delete-orphan",
        order_by="BreakdownRole.created_at",
    )
    character_profiles = relationship(
        "CharacterProfile",
        back_populates="breakdown",
        cascade="all, delete-orphan",
        order_by="CharacterProfile.role_name",
    )
    casting_languages = relationship(
        "CastingLanguage",
        back_populates="breakdown",
        cascade="all, delete-orphan",
        order_by="CastingLanguage.created_at",
    )
    breakdown_sections = relationship(
        "BreakdownSection",
        back_populates="breakdown",
        cascade="all, delete-orphan",
        order_by="BreakdownSection.display_order",
    )
    breakdown_parse_runs = relationship(
        "BreakdownParseRun",
        back_populates="breakdown",
        cascade="all, delete-orphan",
        order_by="BreakdownParseRun.started_at.desc()",
    )

    @property
    def already_tracked(self) -> bool:
        return any(submission.current_status not in {"Passed"} for submission in self.submissions)

    @property
    def tracked_submission_id(self):
        for submission in sorted(self.submissions, key=lambda item: item.created_at, reverse=True):
            if submission.current_status != "Passed":
                return submission.id
        return None

    __table_args__ = (
        CheckConstraint("status IN ('open', 'closed', 'archived')", name="ck_opportunities_status"),
        CheckConstraint(
            "source_type IN ('Platform Discovery', 'Agent Submission', 'Direct Email', "
            "'Social Media', 'Production Website', 'Manual Entry', 'Other')",
            name="ck_opportunities_source_type",
        ),
        CheckConstraint(
            "visibility_status IN ('visible', 'hidden', 'discarded', 'travel_exception')",
            name="ck_opportunities_visibility_status",
        ),
        CheckConstraint(
            "breakdown_classification IN ('Acting Role', 'Background Role', 'Voiceover Role', "
            "'Theater Role', 'Commercial Role', 'Non-Acting Job', 'Crew Job', 'Unknown')",
            name="ck_opportunities_breakdown_classification",
        ),
        CheckConstraint("priority IN ('Low', 'Medium', 'High', 'Urgent')", name="ck_opportunities_priority"),
        CheckConstraint("urgency_score >= 0 AND urgency_score <= 100", name="ck_opportunities_urgency_score"),
        CheckConstraint("quality_score >= 0 AND quality_score <= 100", name="ck_opportunities_quality_score"),
        CheckConstraint(
            "confidence_level IN ('Low', 'Medium', 'High')", name="ck_opportunities_confidence_level"
        ),
        CheckConstraint("risk_level IN ('Low', 'Medium', 'High')", name="ck_opportunities_risk_level"),
        CheckConstraint(
            "demographic_match_status IN ('Match', 'Needs Review', 'Not a Match')",
            name="ck_opportunities_demographic_match_status",
        ),
    )


class BreakdownRole(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "breakdown_roles"

    breakdown_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    billing: Mapped[str | None] = mapped_column(String(120), nullable=True)
    billing_or_role_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    character_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    gender_presentation: Mapped[str | None] = mapped_column(String(160), nullable=True)
    ethnicity_or_cultural_background: Mapped[str | None] = mapped_column(String(255), nullable=True)
    playable_age_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    playable_age_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height_requirements: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vocal_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    dance_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    movement_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    language_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    special_skills: Mapped[str | None] = mapped_column(Text, nullable=True)
    preparation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    union_status: Mapped[str | None] = mapped_column(String(120), nullable=True)
    role_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    fit_status: Mapped[str] = mapped_column(String(40), default="Needs Review", nullable=False)
    fit_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fit_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    extracted_facts: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    ai_inference: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    breakdown = relationship("Opportunity", back_populates="breakdown_roles")
    character_profile = relationship(
        "CharacterProfile",
        back_populates="breakdown_role",
        cascade="all, delete-orphan",
        uselist=False,
    )
    casting_language = relationship(
        "CastingLanguage",
        back_populates="breakdown_role",
        cascade="all, delete-orphan",
        uselist=False,
    )

    __table_args__ = (
        CheckConstraint(
            "fit_status IN ('Strong Fit', 'Possible Fit', 'Stretch Fit', 'Not Fit', 'Needs Review')",
            name="ck_breakdown_roles_fit_status",
        ),
        CheckConstraint(
            "playable_age_min IS NULL OR playable_age_max IS NULL OR playable_age_min <= playable_age_max",
            name="ck_breakdown_roles_playable_age_range",
        ),
        CheckConstraint("fit_score >= 0 AND fit_score <= 100", name="ck_breakdown_roles_fit_score"),
        CheckConstraint("confidence_score >= 0 AND confidence_score <= 100", name="ck_breakdown_roles_confidence_score"),
    )


class CastingLanguage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "casting_languages"

    breakdown_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    breakdown_role_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("breakdown_roles.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    billing: Mapped[str | None] = mapped_column(String(120), nullable=True)
    age_range: Mapped[str | None] = mapped_column(String(80), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(160), nullable=True)
    ethnicity: Mapped[str | None] = mapped_column(String(255), nullable=True)
    union: Mapped[str | None] = mapped_column(String(120), nullable=True)
    compensation: Mapped[str | None] = mapped_column(String(255), nullable=True)
    special_notes: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    breakdown = relationship("Opportunity", back_populates="casting_languages")
    breakdown_role = relationship("BreakdownRole", back_populates="casting_language")


class CharacterProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "character_profiles"

    breakdown_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    breakdown_role_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("breakdown_roles.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    role_name: Mapped[str] = mapped_column(String(255), nullable=False)
    billing: Mapped[str | None] = mapped_column(String(120), nullable=True)
    primary_archetypes: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    secondary_archetypes: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    archetype_confidence_scores: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    personality_traits: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    emotional_traits: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    relationships: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    motivations: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    internal_conflict: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_conflict: Mapped[str | None] = mapped_column(Text, nullable=True)
    emotional_arc: Mapped[str | None] = mapped_column(Text, nullable=True)
    genre: Mapped[str | None] = mapped_column(String(160), nullable=True)
    comedic_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dramatic_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    physical_requirements: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    vocal_requirements: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    movement_requirements: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    casting_language: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    recommended_materials: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    breakdown = relationship("Opportunity", back_populates="character_profiles")
    breakdown_role = relationship("BreakdownRole", back_populates="character_profile")

    __table_args__ = (
        CheckConstraint(
            "comedic_level >= 0 AND comedic_level <= 100",
            name="ck_character_profiles_comedic_level",
        ),
        CheckConstraint(
            "dramatic_level >= 0 AND dramatic_level <= 100",
            name="ck_character_profiles_dramatic_level",
        ),
    )


class BreakdownSection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "breakdown_sections"

    breakdown_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    section_type: Mapped[str] = mapped_column(String(80), nullable=False)
    heading: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    confidence_score: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    breakdown = relationship("Opportunity", back_populates="breakdown_sections")

    __table_args__ = (
        CheckConstraint(
            "section_type IN ('Production Details', 'Audition Information', 'Preparation', 'Roles', "
            "'Character Descriptions', 'Dates', 'Locations', 'Submission Instructions', 'Contact', 'Additional Notes')",
            name="ck_breakdown_sections_section_type",
        ),
        CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 100",
            name="ck_breakdown_sections_confidence_score",
        ),
    )


class BreakdownParseRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "breakdown_parse_runs"

    breakdown_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parser_version: Mapped[str] = mapped_column(String(80), nullable=False, default="breakdown-intelligence-v1")
    parse_mode: Mapped[str] = mapped_column(String(80), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(60), nullable=False, default="running")
    overall_confidence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    breakdown = relationship("Opportunity", back_populates="breakdown_parse_runs")

    __table_args__ = (
        CheckConstraint(
            "parse_mode IN ('Standard Parse', 'Deep Parse', 'Manual Paste Reparse')",
            name="ck_breakdown_parse_runs_parse_mode",
        ),
        CheckConstraint(
            "status IN ('running', 'succeeded', 'failed')",
            name="ck_breakdown_parse_runs_status",
        ),
        CheckConstraint(
            "overall_confidence >= 0 AND overall_confidence <= 100",
            name="ck_breakdown_parse_runs_overall_confidence",
        ),
    )
