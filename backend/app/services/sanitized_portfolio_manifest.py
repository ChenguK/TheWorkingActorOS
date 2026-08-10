from __future__ import annotations

import json
from dataclasses import dataclass, fields
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from uuid import UUID

from app.services.portfolio_seed_ownership_service import (
    PORTFOLIO_DATASET_VERSION,
    PORTFOLIO_PROFILE_ID,
    PORTFOLIO_SEED_NAMESPACE,
    PORTFOLIO_TRAVEL_PREFERENCE_ID,
)


CASTING_GOAL_ID = UUID("6926a996-8c5c-52d4-9687-fcd697aa0db2")
CAREER_MEMORY_ID = UUID("d7ac3ea7-3ebe-5529-b22b-5eafdb4d9a6e")
AGENT_RECOMMENDATION_ID = UUID("04bba855-e70b-5a4e-8133-b07fe2c23220")
RECOMMENDATION_FEEDBACK_ID = UUID("8f0f687d-e781-564d-b0ed-3c9528f4fcaa")

OPPORTUNITY_IDS = (
    UUID("9298ef7e-a248-58ca-8195-ef569b61ffdc"),
    UUID("70f49f55-d091-5f7e-bd73-757d9b08e63c"),
    UUID("039f8c81-ca9c-5086-a26b-88d591176c1e"),
    UUID("feb6af35-8416-5466-b77a-316f8c9382a0"),
    UUID("312d6afa-f095-5eda-8bc5-5c23e64f290b"),
    UUID("ba0e2ef2-38b8-5523-8cfe-cabd338b4fb2"),
    UUID("a77a7780-e97d-52d4-afa7-3c6033fcfec0"),
)
SUBMISSION_IDS = (
    UUID("8550f1a1-9469-521d-9d8e-d22d89105fec"),
    UUID("b9935b51-15bb-5a00-9025-e7e08ed564e8"),
    UUID("920d5725-e518-565c-bc4b-a77c8c7e914e"),
)


class DeadlineBand(str, Enum):
    IMMINENT = "imminent_20_hours"
    URGENT = "urgent_2_days"
    SEVERAL_DAYS = "several_days_5_days"
    ONE_WEEK = "one_week_7_days"
    DISTANT = "distant_14_days"


@dataclass(frozen=True)
class CastingGoalManifest:
    id: UUID
    title: str
    goal_type: str
    target_archetypes: tuple[str, ...]
    target_role_types: tuple[str, ...]
    target_project_types: tuple[str, ...]
    target_markets: tuple[str, ...]
    priority: str
    status: str


@dataclass(frozen=True)
class CareerMemoryManifest:
    id: UUID
    current_focus: str
    current_career_goals: tuple[str, ...]
    stretch_archetypes: tuple[str, ...]
    preferred_project_types: tuple[str, ...]
    preferred_markets: tuple[str, ...]


@dataclass(frozen=True)
class OpportunityManifest:
    id: UUID
    scenario: str
    role: str
    project: str
    description: str
    project_type: str
    role_type: str
    union: str
    location: str
    audition_type: str
    intended_fit: str
    confidence_level: str
    source_reliability_score: float
    language_behavior: str
    deadline_band: DeadlineBand
    submission_deadline: datetime
    audition_deadline: datetime
    callback_date: datetime | None
    shoot_start_date: date
    shoot_end_date: date
    travel_behavior: str
    predicted_action: str
    is_demo_data: bool = False

    @property
    def source_metadata(self) -> dict[str, dict[str, str | int]]:
        return {
            "portfolio_seed": {
                "namespace": PORTFOLIO_SEED_NAMESPACE,
            }
        }


@dataclass(frozen=True)
class SubmissionManifest:
    id: UUID
    opportunity_id: UUID
    current_status: str
    submitted_at: datetime


@dataclass(frozen=True)
class AgentRecommendationManifest:
    id: UUID
    opportunity_id: UUID
    match_type: str
    score: int


@dataclass(frozen=True)
class RecommendationFeedbackManifest:
    id: UUID
    recommendation_id: UUID
    opportunity_id: UUID
    feedback_type: str
    fit_reasons: tuple[str, ...]


@dataclass(frozen=True)
class DerivedRecordPlan:
    record_type: str
    count: int
    ownership_path: str


@dataclass(frozen=True)
class SanitizedPortfolioManifest:
    namespace: str
    dataset_version: int
    as_of: datetime
    actor_profile_id: UUID
    travel_preference_id: UUID
    casting_goal: CastingGoalManifest
    career_memory: CareerMemoryManifest
    opportunities: tuple[OpportunityManifest, ...]
    submissions: tuple[SubmissionManifest, ...]
    recommendation: AgentRecommendationManifest
    feedback: RecommendationFeedbackManifest
    derived_records: tuple[DerivedRecordPlan, ...]


@dataclass(frozen=True)
class RecordPlanSummary:
    record_type: str
    create: int
    update: int
    unchanged: int
    remove: int = 0


def build_sanitized_portfolio_manifest(as_of: datetime) -> SanitizedPortfolioManifest:
    normalized = _aware_utc(as_of)
    opportunities = _opportunities(normalized)
    submissions = (
        SubmissionManifest(
            SUBMISSION_IDS[0], opportunities[0].id, "Submitted", normalized - timedelta(days=1)
        ),
        SubmissionManifest(
            SUBMISSION_IDS[1], opportunities[2].id, "Requested", normalized - timedelta(hours=12)
        ),
        SubmissionManifest(
            SUBMISSION_IDS[2], opportunities[6].id, "Booked", normalized - timedelta(days=3)
        ),
    )
    return SanitizedPortfolioManifest(
        namespace=PORTFOLIO_SEED_NAMESPACE,
        dataset_version=PORTFOLIO_DATASET_VERSION,
        as_of=normalized,
        actor_profile_id=PORTFOLIO_PROFILE_ID,
        travel_preference_id=PORTFOLIO_TRAVEL_PREFERENCE_ID,
        casting_goal=CastingGoalManifest(
            id=CASTING_GOAL_ID,
            title="Build a Film and Television Guest-Star Track",
            goal_type="TV",
            target_archetypes=("Grounded Investigator", "Resilient Advocate", "Strategic Leader"),
            target_role_types=("Guest Star", "Recurring", "Supporting"),
            target_project_types=("Television", "Feature Film"),
            target_markets=("Atlanta", "New York", "Southeast"),
            priority="High",
            status="Active",
        ),
        career_memory=CareerMemoryManifest(
            id=CAREER_MEMORY_ID,
            current_focus="Build sustained Film and Television momentum through selective submissions.",
            current_career_goals=("Book a guest-star role", "Expand recurring-role consideration"),
            stretch_archetypes=("Strategic Leader", "Complex Antagonist", "Period Drama Lead"),
            preferred_project_types=("Television", "Feature Film"),
            preferred_markets=("Atlanta", "New York", "Southeast"),
        ),
        opportunities=opportunities,
        submissions=submissions,
        recommendation=AgentRecommendationManifest(
            id=AGENT_RECOMMENDATION_ID,
            opportunity_id=opportunities[0].id,
            match_type="Strong Match",
            score=91,
        ),
        feedback=RecommendationFeedbackManifest(
            id=RECOMMENDATION_FEEDBACK_ID,
            recommendation_id=AGENT_RECOMMENDATION_ID,
            opportunity_id=opportunities[0].id,
            feedback_type="This Fits Me",
            fit_reasons=("Strong role fit", "Practical self-tape", "Career-aligned project"),
        ),
        derived_records=(
            DerivedRecordPlan("WatchList", 1, "CastingGoal via WorkflowConnectorService"),
            DerivedRecordPlan("SubmissionStatusHistory", 3, "Submission"),
            DerivedRecordPlan("AuditionCalendarEvent", 10, "Submission and Opportunity"),
            DerivedRecordPlan("AuditionJournalEntry", 3, "Submission and Opportunity"),
            DerivedRecordPlan("ActorJournalEntry", 3, "Submission and Opportunity"),
        ),
    )


def project_manifest_dry_run(
    manifest: SanitizedPortfolioManifest,
    *,
    existing_ids: frozenset[UUID] = frozenset(),
    changed_ids: frozenset[UUID] = frozenset(),
    remove_ids: frozenset[UUID] = frozenset(),
) -> tuple[RecordPlanSummary, ...]:
    roots = (
        ("ActorProfile", (manifest.actor_profile_id,)),
        ("TravelPreference", (manifest.travel_preference_id,)),
        ("CastingGoal", (manifest.casting_goal.id,)),
        ("CareerMemory", (manifest.career_memory.id,)),
        ("Opportunities", tuple(item.id for item in manifest.opportunities)),
        ("Submissions", tuple(item.id for item in manifest.submissions)),
        ("AgentRecommendation", (manifest.recommendation.id,)),
        ("RecommendationFeedback", (manifest.feedback.id,)),
    )
    summaries = []
    for record_type, ids in roots:
        updated = sum(item_id in existing_ids and item_id in changed_ids for item_id in ids)
        unchanged = sum(item_id in existing_ids and item_id not in changed_ids for item_id in ids)
        summaries.append(
            RecordPlanSummary(
                record_type=record_type,
                create=len(ids) - unchanged - updated,
                update=updated,
                unchanged=unchanged,
                remove=sum(item_id in remove_ids for item_id in ids),
            )
        )
    summaries.extend(
        RecordPlanSummary(item.record_type, item.count, 0, 0) for item in manifest.derived_records
    )
    return tuple(summaries)


def serialize_manifest(manifest: SanitizedPortfolioManifest) -> str:
    payload = {
        "namespace": manifest.namespace,
        "dataset_version": manifest.dataset_version,
        "as_of": manifest.as_of.isoformat(),
        "actor_profile_id": str(manifest.actor_profile_id),
        "travel_preference_id": str(manifest.travel_preference_id),
        "casting_goal": _record(manifest.casting_goal),
        "career_memory": _record(manifest.career_memory),
        "opportunities": [
            {
                **_record(item),
                "deadline_band": item.deadline_band.value,
                "submission_deadline": item.submission_deadline.isoformat(),
                "audition_deadline": item.audition_deadline.isoformat(),
                "callback_date": item.callback_date.isoformat() if item.callback_date else None,
                "shoot_start_date": item.shoot_start_date.isoformat(),
                "shoot_end_date": item.shoot_end_date.isoformat(),
                "source_metadata": item.source_metadata,
            }
            for item in manifest.opportunities
        ],
        "submissions": [
            {**_record(item), "submitted_at": item.submitted_at.isoformat()}
            for item in manifest.submissions
        ],
        "recommendation": _record(manifest.recommendation),
        "feedback": _record(manifest.feedback),
        "derived_records": [_record(item) for item in manifest.derived_records],
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _opportunities(as_of: datetime) -> tuple[OpportunityManifest, ...]:
    definitions = (
        (
            "strong_self_tape",
            "Forensic Analyst",
            "Signal at Dawn",
            "Strong Fit",
            "Self-Tape",
            "High",
            0.95,
            "SAG-AFTRA",
            "Spanish supports an explicit bilingual preference.",
            DeadlineBand.IMMINENT,
            timedelta(hours=20),
            "Local self-tape with no travel burden.",
            "apply_now",
        ),
        (
            "local_in_person",
            "Public Defender",
            "Crossing Peachtree",
            "Possible Fit",
            "In-Person",
            "High",
            0.90,
            "SAG-AFTRA",
            "No explicit language requirement.",
            DeadlineBand.URGENT,
            timedelta(days=2),
            "Atlanta local-work radius.",
            "review_today",
        ),
        (
            "strategic_stretch",
            "Technology Founder",
            "Second Horizon",
            "Stretch Fit",
            "Virtual",
            "High",
            0.88,
            "Union",
            "English is explicitly required and present.",
            DeadlineBand.SEVERAL_DAYS,
            timedelta(days=5),
            "Virtual audition; production travel reviewed later.",
            "good_stretch_role",
        ),
        (
            "long_range_promising",
            "Investigative Producer",
            "Open Frequency",
            "Strong Fit",
            "Self-Tape",
            "High",
            0.92,
            "SAG-AFTRA",
            "No explicit language requirement.",
            DeadlineBand.DISTANT,
            timedelta(days=14),
            "Self-tape with distant production planning.",
            "apply_now",
        ),
        (
            "lower_confidence_review",
            "Community Organizer",
            "Southbound Stories",
            "Possible Fit",
            "Self-Tape",
            "Low",
            0.66,
            "Non-Union",
            "Spanish is preferred rather than required.",
            DeadlineBand.SEVERAL_DAYS,
            timedelta(days=5),
            "Local self-tape; source confidence requires review.",
            "review_today",
        ),
        (
            "travel_review",
            "Federal Investigator",
            "Northern Passage",
            "Strong Fit",
            "In-Person",
            "Medium",
            0.84,
            "SAG-AFTRA",
            "No explicit language requirement.",
            DeadlineBand.ONE_WEEK,
            timedelta(days=7),
            "New York in-person audition exceeds local radius and needs travel review.",
            "save_for_later",
        ),
        (
            "tracked_booking",
            "Crisis Negotiator",
            "Quiet Leverage",
            "Strong Fit",
            "Self-Tape",
            "High",
            0.94,
            "SAG-AFTRA",
            "English and Spanish are both relevant.",
            DeadlineBand.URGENT,
            timedelta(days=2),
            "Completed self-tape workflow with tracked outcome.",
            "review_today",
        ),
    )
    projects = (
        "Signal at Dawn",
        "Crossing Peachtree",
        "Second Horizon",
        "Open Frequency",
        "Southbound Stories",
        "Northern Passage",
        "Quiet Leverage",
    )
    locations = (
        "Atlanta, GA",
        "Atlanta, GA",
        "Remote",
        "Savannah, GA",
        "Atlanta, GA",
        "New York, NY",
        "Atlanta, GA",
    )
    opportunities = []
    for index, definition in enumerate(definitions):
        (
            scenario,
            role,
            project,
            fit,
            modality,
            confidence,
            reliability,
            union,
            language,
            band,
            offset,
            travel,
            action,
        ) = definition
        deadline = as_of + offset
        callback = deadline + timedelta(days=6) if scenario == "tracked_booking" else None
        shoot_start = (deadline + timedelta(days=20)).date()
        opportunities.append(
            OpportunityManifest(
                id=OPPORTUNITY_IDS[index],
                scenario=scenario,
                role=role,
                project=projects[index],
                description=f"Fictional Film and Television casting notice for {role} in {project}.",
                project_type="Television" if index != 3 else "Feature Film",
                role_type="Guest Star" if index in {0, 1, 5, 6} else "Supporting",
                union=union,
                location=locations[index],
                audition_type=modality,
                intended_fit=fit,
                confidence_level=confidence,
                source_reliability_score=reliability,
                language_behavior=language,
                deadline_band=band,
                submission_deadline=deadline,
                audition_deadline=deadline + timedelta(days=2),
                callback_date=callback,
                shoot_start_date=shoot_start,
                shoot_end_date=shoot_start + timedelta(days=5),
                travel_behavior=travel,
                predicted_action=action,
            )
        )
    return tuple(opportunities)


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("sanitized portfolio manifest as_of must be timezone-aware")
    return value.astimezone(timezone.utc)


def _record(value: object) -> dict[str, object]:
    result: dict[str, object] = {}
    for field in fields(value):  # type: ignore[arg-type]
        item = getattr(value, field.name)
        if isinstance(item, UUID):
            result[field.name] = str(item)
        elif isinstance(item, tuple):
            result[field.name] = list(item)
        else:
            result[field.name] = item
    return result
