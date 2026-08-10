from __future__ import annotations

import re
from dataclasses import FrozenInstanceError
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

from app.db.models import ActorProfile
from app.services.executive_intelligence_service import ExecutiveIntelligenceService
from app.services.journal_service import JournalService
from app.services.portfolio_seed_ownership_service import (
    PORTFOLIO_DATASET_VERSION,
    PORTFOLIO_PROFILE_ID,
    PORTFOLIO_SEED_NAMESPACE,
    PORTFOLIO_TRAVEL_PREFERENCE_ID,
)
from app.services.sanitized_portfolio_manifest import (
    AGENT_RECOMMENDATION_ID,
    CAREER_MEMORY_ID,
    CASTING_GOAL_ID,
    OPPORTUNITY_IDS,
    RECOMMENDATION_FEEDBACK_ID,
    RecordPlanSummary,
    SUBMISSION_IDS,
    build_sanitized_portfolio_manifest,
    project_manifest_dry_run,
    serialize_manifest,
)
from app.services.watch_list_service import WatchListService


AS_OF = datetime(2030, 4, 10, 14, 30, tzinfo=timezone.utc)


def test_manifest_is_immutable_bounded_and_deterministically_ordered() -> None:
    manifest = build_sanitized_portfolio_manifest(AS_OF)

    with pytest.raises(FrozenInstanceError):
        manifest.namespace = "changed"  # type: ignore[misc]

    assert manifest.namespace == PORTFOLIO_SEED_NAMESPACE
    assert manifest.dataset_version == PORTFOLIO_DATASET_VERSION == 1
    assert manifest.actor_profile_id == PORTFOLIO_PROFILE_ID
    assert manifest.travel_preference_id == PORTFOLIO_TRAVEL_PREFERENCE_ID
    assert manifest.casting_goal.id == CASTING_GOAL_ID
    assert manifest.career_memory.id == CAREER_MEMORY_ID
    assert tuple(item.id for item in manifest.opportunities) == OPPORTUNITY_IDS
    assert tuple(item.id for item in manifest.submissions) == SUBMISSION_IDS
    assert manifest.recommendation.id == AGENT_RECOMMENDATION_ID
    assert manifest.feedback.id == RECOMMENDATION_FEEDBACK_ID
    assert len(manifest.opportunities) == 7
    assert len(manifest.submissions) == 3
    assert [(item.record_type, item.count) for item in manifest.derived_records] == [
        ("WatchList", 1),
        ("SubmissionStatusHistory", 3),
        ("AuditionCalendarEvent", 10),
        ("AuditionJournalEntry", 3),
        ("ActorJournalEntry", 3),
    ]


def test_opportunities_are_owned_normal_and_sanitized() -> None:
    manifest = build_sanitized_portfolio_manifest(AS_OF)
    forbidden = re.compile(r"\b(demo|example|sample|test)\b", re.IGNORECASE)
    private_sentinels = {
        "private-user",
        "real actor",
        "example.com",
        "@",
        "phone-number-sentinel",
    }

    for opportunity in manifest.opportunities:
        vulnerable_text = " ".join(
            (
                opportunity.role,
                opportunity.project,
                opportunity.description,
                opportunity.project_type,
                opportunity.role_type,
                opportunity.location,
            )
        )
        assert not forbidden.search(vulnerable_text)
        assert opportunity.source_metadata == {
            "portfolio_seed": {"namespace": PORTFOLIO_SEED_NAMESPACE}
        }
        assert opportunity.is_demo_data is False
        assert not any(sentinel in vulnerable_text.lower() for sentinel in private_sentinels)

    serialized = serialize_manifest(manifest).lower()
    assert not any(sentinel in serialized for sentinel in private_sentinels)


def test_relative_dates_derive_from_one_aware_as_of_and_are_internally_ordered() -> None:
    manifest = build_sanitized_portfolio_manifest(AS_OF)
    offsets = (20, 48, 120, 336, 120, 168, 48)

    for opportunity, hours in zip(manifest.opportunities, offsets, strict=True):
        assert opportunity.submission_deadline == AS_OF + timedelta(hours=hours)
        assert opportunity.audition_deadline == opportunity.submission_deadline + timedelta(days=2)
        assert opportunity.shoot_start_date > opportunity.audition_deadline.date()
        assert opportunity.shoot_end_date > opportunity.shoot_start_date
        if opportunity.callback_date:
            assert opportunity.callback_date > opportunity.audition_deadline

    for submission in manifest.submissions:
        assert submission.submitted_at.tzinfo is not None


def test_same_instant_in_different_timezones_serializes_identically() -> None:
    new_york = AS_OF.astimezone(ZoneInfo("America/New_York"))

    assert serialize_manifest(build_sanitized_portfolio_manifest(AS_OF)) == serialize_manifest(
        build_sanitized_portfolio_manifest(new_york)
    )


def test_same_as_of_produces_identical_serialization() -> None:
    first = build_sanitized_portfolio_manifest(AS_OF)
    second = build_sanitized_portfolio_manifest(AS_OF)

    assert serialize_manifest(first) == serialize_manifest(second)


def test_naive_as_of_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        build_sanitized_portfolio_manifest(datetime(2030, 4, 10, 14, 30))


def test_manifest_contains_no_deferred_record_types() -> None:
    manifest = build_sanitized_portfolio_manifest(AS_OF)
    serialized = serialize_manifest(manifest)

    for deferred in (
        "Asset",
        "SubmissionAsset",
        "DreamRoleTarget",
        "Archetype",
        "CallbackEvent",
    ):
        assert deferred not in serialized


def test_dry_run_projection_is_pure_and_represents_existing_profile_configuration() -> None:
    manifest = build_sanitized_portfolio_manifest(AS_OF)
    before = serialize_manifest(manifest)
    summaries = project_manifest_dry_run(
        manifest,
        existing_ids=frozenset({manifest.actor_profile_id, manifest.travel_preference_id}),
    )

    assert summaries[:4] == (
        RecordPlanSummary("ActorProfile", 0, 0, 1, 0),
        RecordPlanSummary("TravelPreference", 0, 0, 1, 0),
        RecordPlanSummary("CastingGoal", 1, 0, 0, 0),
        RecordPlanSummary("CareerMemory", 1, 0, 0, 0),
    )
    assert serialize_manifest(manifest) == before


def test_dry_run_projection_reports_update_and_remove_counts() -> None:
    manifest = build_sanitized_portfolio_manifest(AS_OF)
    summaries = project_manifest_dry_run(
        manifest,
        existing_ids=frozenset({CASTING_GOAL_ID}),
        changed_ids=frozenset({CASTING_GOAL_ID}),
        remove_ids=frozenset({RECOMMENDATION_FEEDBACK_ID}),
    )
    by_type = {summary.record_type: summary for summary in summaries}

    assert by_type["CastingGoal"].update == 1
    assert by_type["CastingGoal"].create == 0
    assert by_type["RecommendationFeedback"].remove == 1


def test_existing_watchlist_refresh_and_journal_record_primitives_do_not_commit() -> None:
    watch_db = MagicMock()
    watch_db.scalars.return_value.all.return_value = []
    WatchListService(watch_db).refresh_all()

    journal_db = MagicMock()
    journal_db.scalar.return_value = None
    JournalService(journal_db).record_once(
        event_type="Submitted to Role",
        title="Fictional submitted role",
        entry_date=date(2030, 4, 10),
    )

    watch_db.commit.assert_not_called()
    journal_db.add.assert_called_once()
    journal_db.commit.assert_not_called()
    journal_db.flush.assert_not_called()


def test_current_career_memory_public_service_owns_commit() -> None:
    db = MagicMock()
    db.scalars.return_value.first.return_value = None
    actor = ActorProfile(id=PORTFOLIO_PROFILE_ID, name="Fictional")

    memory = ExecutiveIntelligenceService(db).get_or_create_memory(actor)

    assert memory.actor_profile_id == PORTFOLIO_PROFILE_ID
    db.add.assert_called_once_with(memory)
    db.commit.assert_called_once_with()
