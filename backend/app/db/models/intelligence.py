from datetime import date

from sqlalchemy import CheckConstraint, Column, Date, ForeignKey, String, Table, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


RelationshipOpportunity = Table(
    "relationship_opportunities",
    Base.metadata,
    Column(
        "relationship_id",
        UUID(as_uuid=True),
        ForeignKey("actor_relationships.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "opportunity_id",
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


RelationshipSubmission = Table(
    "relationship_submissions",
    Base.metadata,
    Column(
        "relationship_id",
        UUID(as_uuid=True),
        ForeignKey("actor_relationships.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "submission_id",
        UUID(as_uuid=True),
        ForeignKey("submissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class CastingOffice(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "casting_offices"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    source_platform: Mapped[str | None] = mapped_column(String(120), nullable=True)
    project_history: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    submission_history: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    callback_history: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    booking_history: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    contacts = relationship("CastingContact", back_populates="office", cascade="all, delete-orphan")
    opportunities = relationship("Opportunity", back_populates="casting_office")


class CastingContact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "casting_contacts"

    casting_office_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("casting_offices.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(120), nullable=False, default="Casting Director")
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    office = relationship("CastingOffice", back_populates="contacts")


class ActorRelationship(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "actor_relationships"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role_title: Mapped[str] = mapped_column(String(120), nullable=False)
    company_office: Mapped[str | None] = mapped_column(String(255), nullable=True)
    projects: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_contact_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    relationship_strength: Mapped[str] = mapped_column(String(40), default="Warm", nullable=False)
    linked_outcomes: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    linked_opportunities = relationship("Opportunity", secondary=RelationshipOpportunity)
    linked_submissions = relationship("Submission", secondary=RelationshipSubmission)

    @property
    def linked_opportunity_ids(self) -> list[UUID]:
        return [item.id for item in self.linked_opportunities]

    @property
    def linked_submission_ids(self) -> list[UUID]:
        return [item.id for item in self.linked_submissions]

    __table_args__ = (
        CheckConstraint(
            "role_title IN ('Casting Director', 'Casting Office', 'Producer', 'Director', "
            "'Writer', 'Agent', 'Manager', 'Coach')",
            name="ck_actor_relationships_role_title",
        ),
        CheckConstraint(
            "relationship_strength IN ('Cold', 'Warm', 'Strong', 'Champion')",
            name="ck_actor_relationships_strength",
        ),
    )


class SelfTape(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "self_tapes"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    role_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    archetypes: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    linked_opportunity_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True
    )
    linked_submission_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("submissions.id", ondelete="SET NULL"), nullable=True
    )
    outcome: Mapped[str | None] = mapped_column(String(80), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    date_created: Mapped[date] = mapped_column(Date, nullable=False)

    linked_opportunity = relationship("Opportunity")
    linked_submission = relationship("Submission")


class AuditionJournalEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "audition_journal_entries"

    submission_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("submissions.id", ondelete="SET NULL"), nullable=True
    )
    opportunity_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    preparation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    performance_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    casting_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    wardrobe_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    emotional_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    submission = relationship("Submission")
    opportunity = relationship("Opportunity")


class CallbackEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "callback_events"

    submission_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=True, index=True
    )
    opportunity_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=True, index=True
    )
    event_name: Mapped[str] = mapped_column(String(120), nullable=False)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False, default="First Callback")
    event_datetime: Mapped[date | None] = mapped_column(Date, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_virtual: Mapped[bool] = mapped_column(default=False, nullable=False)
    preparation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(80), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    submission = relationship("Submission")
    opportunity = relationship("Opportunity")


class CommunicationLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "communication_logs"

    representation_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("representations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    opportunity_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True, index=True
    )
    submission_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("submissions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_needed: Mapped[bool] = mapped_column(default=False, nullable=False)
    follow_up_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    representation = relationship("Representation")
    opportunity = relationship("Opportunity")
    submission = relationship("Submission")


class AuditionPreparationBrief(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "audition_preparation_briefs"

    opportunity_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False
    )
    submission_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("submissions.id", ondelete="SET NULL"), nullable=True
    )
    brief: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    opportunity = relationship("Opportunity")
    submission = relationship("Submission")


class MaterialCreationPlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "material_creation_plans"

    career_task_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("career_development_tasks.id", ondelete="SET NULL"), nullable=True
    )
    missing_asset: Mapped[str] = mapped_column(String(255), nullable=False)
    target_archetype: Mapped[str | None] = mapped_column(String(120), nullable=True)
    plan_status: Mapped[str] = mapped_column(String(80), default="Pending Review", nullable=False)
    plan: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    career_task = relationship("CareerDevelopmentTask")

    __table_args__ = (
        CheckConstraint(
            "plan_status IN ('Pending Review', 'Approved', 'Denied')",
            name="ck_material_creation_plans_plan_status",
        ),
    )


class ScriptSource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "script_sources"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_type: Mapped[str] = mapped_column(String(120), nullable=False)
    rights_status: Mapped[str] = mapped_column(String(80), nullable=False, default="Unknown")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved: Mapped[bool] = mapped_column(default=False, nullable=False)

    scene_candidates = relationship("SceneCandidate", back_populates="script_source")

    __table_args__ = (
        CheckConstraint(
            "rights_status IN ('Public Domain', 'Royalty-Free', 'Original / User-Owned', 'Licensed', 'Permission Required', 'Unknown')",
            name="ck_script_sources_rights_status",
        ),
    )


class SceneCandidate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "scene_candidates"

    script_source_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("script_sources.id", ondelete="SET NULL"), nullable=True, index=True
    )
    career_task_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("career_development_tasks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    result_type: Mapped[str] = mapped_column(String(80), default="Specific Scene", nullable=False)
    rights_status: Mapped[str] = mapped_column(String(80), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    logline: Mapped[str] = mapped_column(Text, nullable=False)
    scene_brief: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    action_status: Mapped[str] = mapped_column(String(80), default="Candidate", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    script_source = relationship("ScriptSource", back_populates="scene_candidates")
    career_task = relationship("CareerDevelopmentTask")

    __table_args__ = (
        CheckConstraint(
            "result_type IN ('Specific Scene', 'Specific Monologue', 'Script Library', 'Resource Guide', 'Music / Sound Library', 'Dead / Fetch Failed', 'Rights Unknown', 'Not Useful')",
            name="ck_scene_candidates_result_type",
        ),
        CheckConstraint(
            "rights_status IN ('Public Domain', 'Royalty-Free', 'Original / User-Owned', 'Licensed', 'Permission Required', 'Unknown')",
            name="ck_scene_candidates_rights_status",
        ),
        CheckConstraint(
            "action_status IN ('Candidate', 'Saved', 'Permission Requested', 'Original Brief')",
            name="ck_scene_candidates_action_status",
        ),
    )


class CareerPathSimulation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "career_path_simulations"

    actor_profile_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("actor_profiles.id", ondelete="CASCADE"), nullable=False
    )
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    actor_profile = relationship("ActorProfile")


class DreamRoleTarget(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "dream_role_targets"

    actor_profile_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("actor_profiles.id", ondelete="CASCADE"), nullable=False
    )
    target_type: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_archetypes: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    target_genres: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    target_offices: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    actor_profile = relationship("ActorProfile")

    __table_args__ = (
        CheckConstraint(
            "target_type IN ('Role', 'Show', 'Genre', 'Casting Office', 'Studio', 'Archetype')",
            name="ck_dream_role_targets_type",
        ),
    )


class QuarterlyCareerReview(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "quarterly_career_reviews"

    actor_profile_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("actor_profiles.id", ondelete="CASCADE"), nullable=False
    )
    year: Mapped[int] = mapped_column(nullable=False)
    quarter: Mapped[int] = mapped_column(nullable=False)
    report: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    actor_profile = relationship("ActorProfile")

    __table_args__ = (
        CheckConstraint("quarter >= 1 AND quarter <= 4", name="ck_quarterly_career_reviews_quarter"),
    )
