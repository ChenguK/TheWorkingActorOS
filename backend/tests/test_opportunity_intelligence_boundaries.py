from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.agents.strategy_agent import StrategyAgent
from app.db.models import AgentRecommendation
from app.services.breakdown_deadline_service import DeadlineValidationResult
from app.services.opportunity_intelligence_service import OpportunityIntelligenceService
from tests.intelligence_builders import (
    FIXED_RECOMMENDATION_ID,
    actor_profile,
    boundary_snapshot,
    fixed_as_of,
    opportunity,
    opportunity_snapshot,
    parsed_role,
    scoring_context,
)


class _ScalarResult:
    def __init__(self, first=None, items=()):
        self._first = first
        self._items = list(items)

    def first(self):
        return self._first

    def __iter__(self):
        return iter(self._items)


class _IntelligenceDatabase:
    def __init__(self, actor):
        self.actor = actor

    def scalars(self, _statement):
        return _ScalarResult(first=self.actor)


def _valid_deadline_result() -> DeadlineValidationResult:
    return DeadlineValidationResult(
        status="Valid", parsed_dates={"submission_deadline": "2026-08-03"}
    )


def _run_controlled_enrichment(item, actor=None):
    actor = actor or actor_profile()
    database = _IntelligenceDatabase(actor)
    service = OpportunityIntelligenceService(database)
    with (
        patch(
            "app.services.opportunity_intelligence_service.BreakdownDeadlineService.apply_to_opportunity",
            return_value=_valid_deadline_result(),
        ),
        patch("app.services.opportunity_intelligence_service.DemographicMatchService.apply"),
        patch(
            "app.services.opportunity_intelligence_service.BreakdownRoleService.sync_from_details"
        ),
        patch(
            "app.services.opportunity_intelligence_service.CharacterIntelligenceEngine.run_for_opportunity"
        ),
        patch(
            "app.services.opportunity_intelligence_service.WatchListService.apply_to_opportunity"
        ),
        patch.object(service, "apply_audition_visibility", return_value=item),
        patch.object(service, "apply_hard_eligibility", return_value=item),
        patch.object(service, "_apply_goal_priority"),
    ):
        return service.enrich(item)


@pytest.mark.parametrize(
    ("hours", "expected"),
    [(12, 95), (60, 80), (120, 55), (240, 25), (-1, 100)],
)
def test_urgency_uses_soonest_deadline_relative_to_current_utc_time(hours, expected):
    as_of = fixed_as_of()
    item = opportunity(submission_deadline=as_of + timedelta(hours=hours))
    with patch("app.services.opportunity_intelligence_service.datetime") as clock:
        clock.now.return_value = as_of
        score = OpportunityIntelligenceService(db=None)._urgency_score(item)
    assert score == expected
    clock.now.assert_called_once_with(timezone.utc)


def test_urgency_uses_earliest_of_submission_and_audition_deadlines():
    as_of = fixed_as_of()
    item = opportunity(
        submission_deadline=as_of + timedelta(days=10),
        audition_deadline=as_of + timedelta(hours=20),
    )
    with patch("app.services.opportunity_intelligence_service.datetime") as clock:
        clock.now.return_value = as_of
        assert OpportunityIntelligenceService(db=None)._urgency_score(item) == 95


def test_missing_deadline_has_current_fixed_urgency():
    assert OpportunityIntelligenceService(db=None)._urgency_score(opportunity()) == 20


def test_naive_deadline_is_currently_interpreted_as_utc():
    as_of = fixed_as_of()
    item = opportunity(submission_deadline=datetime(2026, 8, 3, 0, 0))
    with patch("app.services.opportunity_intelligence_service.datetime") as clock:
        clock.now.return_value = as_of
        clock.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        assert OpportunityIntelligenceService(db=None)._urgency_score(item) == 95


def test_fixed_time_produces_repeatable_urgency():
    as_of = fixed_as_of()
    item = opportunity(submission_deadline=as_of + timedelta(hours=48))
    with patch("app.services.opportunity_intelligence_service.datetime") as clock:
        clock.now.return_value = as_of
        service = OpportunityIntelligenceService(db=None)
        assert [service._urgency_score(item) for _ in range(3)] == [80, 80, 80]


def test_expired_enrichment_archives_and_zeroes_existing_scores():
    item = opportunity(
        submission_deadline=datetime(2020, 1, 1, tzinfo=timezone.utc),
        urgency_score=73,
        quality_score=81,
    )
    unrelated_before = {
        "original_post_url": item.original_post_url,
        "normalized_key": item.normalized_key,
        "is_duplicate": item.is_duplicate,
        "production_details": dict(item.production_details),
        "role_details": dict(item.role_details),
        "ai_inference": dict(item.ai_inference),
    }
    result = OpportunityIntelligenceService(db=None).enrich(item)
    assert result is item
    assert (item.urgency_score, item.quality_score) == (0, 0)
    assert item.visibility_status == "discarded"
    assert item.status == "archived"
    assert item.hidden_by_rule == "deadline_expired"
    assert item.confidence_level == "High"
    assert item.risk_level == "High"
    assert item.source_metadata["date_validation"]["status"] == "Expired"
    assert {key: getattr(item, key) for key in unrelated_before} == unrelated_before


def test_controlled_enrich_updates_only_current_score_projection_fields():
    item = opportunity(
        submission_deadline=fixed_as_of() + timedelta(hours=20),
        breakdown_roles=[parsed_role()],
        urgency_score=1,
        quality_score=2,
    )
    before = boundary_snapshot(item)
    with patch("app.services.opportunity_intelligence_service.datetime") as clock:
        clock.now.return_value = fixed_as_of()
        result = _run_controlled_enrichment(item)
    assert result is item
    assert item.urgency_score == 95
    assert item.quality_score == 75
    assert item.quality_explanation == (
        "Quality reflects union-aligned, high-reliability source, detailed role information."
    )
    assert item.confidence_level == "High"
    assert item.risk_level == "Medium"
    assert item.priority == "High"
    assert boundary_snapshot(item) == before


def test_quality_formula_rewards_listing_facts_not_actor_compatibility():
    service = OpportunityIntelligenceService(db=None)
    item = opportunity(
        breakdown_roles=[parsed_role()],
        union="SAG-AFTRA",
        travel_covered=True,
        housing_covered=True,
        source_reliability_score=0.9,
        visibility_status="visible",
    )
    assert service._quality_score(item) == (
        95,
        "Quality reflects union-aligned, travel covered, housing covered, high-reliability source, detailed role information.",
    )

    item.demographic_match_status = "Not a Match"
    item.role_details = {"language": "Mandarin"}
    item.source_metadata["trust_verification"] = {"status": "Blocked"}
    assert service._quality_score(item)[0] == 95


def test_quality_returns_ten_when_parsed_roles_have_no_fit():
    item = opportunity(breakdown_roles=[parsed_role(fit_status="Not Fit")])
    assert OpportunityIntelligenceService(db=None)._quality_score(item) == (
        10,
        "Low priority because no parsed role currently fits the actor profile.",
    )


def test_quality_missing_fit_uses_available_listing_facts():
    item = opportunity(
        breakdown_roles=[],
        union="Non-Union",
        description="Short",
        source_reliability_score=0.4,
        travel_covered=None,
        housing_covered=None,
    )
    assert OpportunityIntelligenceService(db=None)._quality_score(item) == (
        35,
        "Quality reflects limited available details.",
    )


@pytest.mark.parametrize("visibility", ["hidden", "travel_exception"])
def test_quality_penalizes_hidden_and_travel_exception_equally(visibility):
    item = opportunity(
        breakdown_roles=[parsed_role()],
        visibility_status=visibility,
        union="Non-Union",
        description="Short",
        source_reliability_score=0.4,
    )
    assert OpportunityIntelligenceService(db=None)._quality_score(item)[0] == 10


@pytest.mark.parametrize("audition_type", ["Self-Tape", "Virtual"])
def test_remote_modality_resets_travel_and_is_visible(audition_type):
    item = opportunity(
        audition_type=audition_type,
        audition_drive_time=9,
        audition_travel_hours=9,
        visibility_status="hidden",
    )
    OpportunityIntelligenceService(db=None).apply_audition_visibility(item)
    assert item.audition_drive_time == 0
    assert item.audition_travel_hours == 0
    assert item.visibility_status == "visible"
    assert item.manual_review_required is False


def test_local_in_person_remains_visible_with_manual_estimate():
    item = opportunity(
        audition_type="In-Person",
        audition_location="Philadelphia, PA",
        audition_travel_hours=1.0,
    )
    OpportunityIntelligenceService(db=None).apply_hard_eligibility(item, actor_profile())
    assert item.visibility_status == "visible"
    assert item.hidden_by_rule is None


def test_nonlocal_in_person_is_current_travel_exception():
    item = opportunity(
        audition_type="In-Person",
        audition_location="New York, NY",
        audition_travel_hours=3.0,
    )
    OpportunityIntelligenceService(db=None).apply_hard_eligibility(item, actor_profile())
    assert item.visibility_status == "travel_exception"
    assert item.hidden_by_rule == "travel_exception"


def test_excluded_role_type_is_hard_travel_independent_rejection():
    item = opportunity(role_type="Crew", audition_type="Self-Tape")
    OpportunityIntelligenceService(db=None).apply_hard_eligibility(item, actor_profile())
    assert item.visibility_status == "discarded"
    assert item.hidden_by_rule == "dealbreaker_role_type"


def test_demographic_mismatch_is_a_hard_eligibility_rejection():
    item = opportunity(demographic_match_status="Not a Match")
    OpportunityIntelligenceService(db=None).apply_hard_eligibility(item, actor_profile())
    assert item.visibility_status == "discarded"
    assert item.hidden_by_rule == "dealbreaker_demographic_mismatch"


def test_availability_conflict_is_a_hard_eligibility_rejection():
    item = opportunity()
    service = OpportunityIntelligenceService(db=None)
    with patch.object(
        service,
        "_availability_conflict",
        return_value="Availability conflict: Test booking overlaps 2026-08-04.",
    ):
        service.apply_hard_eligibility(item, actor_profile())
    assert item.visibility_status == "discarded"
    assert item.hidden_by_rule == "dealbreaker_availability"


def test_missing_in_person_travel_information_is_hidden_for_review():
    item = opportunity(
        audition_type="In-Person", audition_location=None, audition_travel_hours=None
    )
    OpportunityIntelligenceService(db=None).apply_audition_visibility(item)
    assert item.visibility_status == "hidden"
    assert item.hidden_by_rule == "audition_location_needs_info"
    assert item.manual_review_required is True


def test_confidence_uses_parse_confidence_completeness_and_source_reliability_not_trust_status():
    service = OpportunityIntelligenceService(db=None)
    item = opportunity()
    assert service._confidence_level(item) == "High"

    item.source_metadata["breakdown_parse_confidence"] = 60
    assert service._confidence_level(item) == "Low"

    item.source_metadata["breakdown_parse_confidence"] = 92
    item.source_metadata["trust_verification"] = {"status": "Blocked"}
    assert service._confidence_level(item) == "High"

    item.submission_deadline = None
    item.audition_type = ""
    assert service._confidence_level(item) == "Medium"


@pytest.mark.parametrize(
    ("visibility", "audition_type", "travel_hours", "expected_level"),
    [
        ("discarded", "Self-Tape", 0, "High"),
        ("hidden", "Self-Tape", 0, "High"),
        ("travel_exception", "In-Person", 3, "High"),
        ("visible", "In-Person", None, "High"),
        ("visible", "Self-Tape", 0, "Medium"),
    ],
)
def test_risk_is_derived_from_visibility_and_known_travel(
    visibility, audition_type, travel_hours, expected_level
):
    item = opportunity(
        visibility_status=visibility,
        audition_type=audition_type,
        audition_travel_hours=travel_hours,
        travel_covered=False,
        housing_covered=False,
    )
    level, explanation = OpportunityIntelligenceService(db=None)._risk(item)
    assert level == expected_level
    assert explanation


@pytest.mark.parametrize(
    ("classification", "expected_confidence"),
    [("Unknown", "Low"), ("Crew Job", "Low")],
)
def test_unknown_and_rejected_classifications_zero_scores(classification, expected_confidence):
    item = opportunity(breakdown_classification=classification, urgency_score=75, quality_score=80)
    with patch(
        "app.services.opportunity_intelligence_service.BreakdownDeadlineService.apply_to_opportunity",
        return_value=_valid_deadline_result(),
    ):
        OpportunityIntelligenceService(db=None).enrich(item)
    assert (item.urgency_score, item.quality_score) == (0, 0)
    assert item.confidence_level == expected_confidence
    assert item.risk_level == "High"


def test_duplicate_identity_and_provider_metadata_are_not_quality_inputs():
    ordinary = opportunity(is_duplicate=False)
    duplicate = opportunity(is_duplicate=True)
    assert OpportunityIntelligenceService(db=None)._quality_score(ordinary) == (
        OpportunityIntelligenceService(db=None)._quality_score(duplicate)
    )
    assert duplicate.normalized_key == "test-procedural|detective|philadelphia"
    assert duplicate.source_metadata["provider"] == "test-provider"


def test_user_rejection_state_is_restored_after_enrichment():
    item = opportunity(
        hidden_by_rule="user_rejected",
        hidden_reason="Actor rejected this listing.",
        rejection_reason="Actor rejected this listing.",
        highlighted_text_as_rejection_reason="Not my type",
        visibility_status="discarded",
        status="archived",
        manual_review_required=False,
    )
    preserved = boundary_snapshot(item)
    with patch("app.services.opportunity_intelligence_service.datetime") as clock:
        clock.now.return_value = fixed_as_of()
        _run_controlled_enrichment(item)
    assert item.visibility_status == preserved["visibility_status"]
    assert item.status == preserved["status"]
    assert item.hidden_by_rule == preserved["hidden_by_rule"]
    assert item.hidden_reason == preserved["hidden_reason"]
    assert item.rejection_reason == preserved["rejection_reason"]
    assert (
        item.highlighted_text_as_rejection_reason
        == preserved["highlighted_text_as_rejection_reason"]
    )
    assert item.source_metadata["user_rejected"] is True
    assert item.source_metadata["provider"] == "test-provider"
    assert item.source_metadata["discovery"] == {"run_id": "test-run", "candidate_index": 0}


def test_complete_snapshot_helper_detects_no_changes():
    item = opportunity()
    before = opportunity_snapshot(item)
    _ = (item.role, item.project, scoring_context(), fixed_as_of())
    assert opportunity_snapshot(item) == before


def test_strategy_agent_owns_recommendation_score_without_overwriting_opportunity_scores():
    actor = actor_profile()
    item = opportunity(urgency_score=31, quality_score=62, breakdown_roles=[])
    database = MagicMock()
    database.scalars.side_effect = [
        _ScalarResult(items=[]),
        _ScalarResult(first=None),
        _ScalarResult(first=None),
    ]
    database.refresh.side_effect = lambda recommendation: setattr(
        recommendation, "id", FIXED_RECOMMENDATION_ID
    )
    before_scores = (item.urgency_score, item.quality_score)

    recommendation = StrategyAgent(database).analyze(item, actor)

    assert isinstance(recommendation, AgentRecommendation)
    assert recommendation.id == FIXED_RECOMMENDATION_ID
    assert recommendation.score == 48
    assert recommendation.score_breakdown == {
        "role_fit": 20,
        "production_travel": 8,
        "audition_feasibility": 15,
        "asset_package": 0,
        "learning_signal": 5,
    }
    assert (item.urgency_score, item.quality_score) == before_scores
    database.add.assert_called_once_with(recommendation)
    database.commit.assert_called_once_with()
    database.refresh.assert_called_once_with(recommendation)


def test_strategy_agent_creates_a_new_recommendation_on_each_analysis():
    actor = actor_profile()
    item = opportunity(breakdown_roles=[])
    database = MagicMock()
    database.scalars.side_effect = [
        _ScalarResult(items=[]),
        _ScalarResult(first=None),
        _ScalarResult(first=None),
        _ScalarResult(items=[]),
        _ScalarResult(first=None),
        _ScalarResult(first=None),
    ]

    first = StrategyAgent(database).analyze(item, actor)
    second = StrategyAgent(database).analyze(item, actor)

    assert first is not second
    assert first.score == second.score == 48
    assert database.add.call_count == 2
    assert database.commit.call_count == 2
