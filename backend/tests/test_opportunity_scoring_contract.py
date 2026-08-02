from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
import json
from unittest.mock import MagicMock, patch

import pytest

from app.services.opportunity_intelligence_service import OpportunityIntelligenceService
from app.services.opportunity_score import (
    HARD_OVERRIDE_REASON_ORDER,
    MAX_SCORE_EXPLANATION_LENGTH,
    NEGATIVE_CONTRIBUTOR_LIMIT,
    OPPORTUNITY_SCORE_BASELINE,
    OPPORTUNITY_SCORING_VERSION,
    POSITIVE_CONTRIBUTOR_LIMIT,
    SCORE_CATEGORY_CAPS,
    SCORE_CATEGORY_ORDER,
    OpportunityScoringContext,
    ScoringContextMatch,
    ScoreCategory,
    ScoreFactor,
    build_opportunity_score,
)
from tests.intelligence_builders import (
    actor_profile,
    fixed_as_of,
    opportunity,
    opportunity_snapshot,
)


def factor(
    factor_id: str = "match.test",
    category: ScoreCategory = ScoreCategory.MATCH_QUALITY,
    points: int = 5,
    priority: int = 10,
) -> ScoreFactor:
    return ScoreFactor(
        id=factor_id,
        category=category,
        points=points,
        explanation=f"Deterministic explanation for {factor_id}.",
        priority=priority,
    )


def serialized(result) -> str:
    return json.dumps(result.as_dict(), separators=(",", ":"), ensure_ascii=True)


def test_contract_constants_match_version_one_design():
    assert OPPORTUNITY_SCORING_VERSION == 1
    assert OPPORTUNITY_SCORE_BASELINE == 50
    assert POSITIVE_CONTRIBUTOR_LIMIT == 3
    assert NEGATIVE_CONTRIBUTOR_LIMIT == 3
    assert tuple(category.value for category in SCORE_CATEGORY_ORDER) == (
        "match_quality",
        "career_value",
        "practicality",
        "confidence",
        "actor_interest",
    )
    assert SCORE_CATEGORY_CAPS == {
        ScoreCategory.MATCH_QUALITY: (-35, 30),
        ScoreCategory.CAREER_VALUE: (-10, 20),
        ScoreCategory.PRACTICALITY: (-25, 20),
        ScoreCategory.CONFIDENCE: (-20, 15),
        ScoreCategory.ACTOR_INTEREST: (-20, 15),
    }


def test_valid_factor_is_immutable_and_json_safe():
    value = factor()
    assert value.as_dict() == {
        "id": "match.test",
        "category": "match_quality",
        "points": 5,
        "explanation": "Deterministic explanation for match.test.",
        "priority": 10,
    }
    with pytest.raises(FrozenInstanceError):
        value.points = 9


@pytest.mark.parametrize(
    "overrides",
    [
        {"id": ""},
        {"id": "Invalid Factor"},
        {"category": "unsupported"},
        {"points": 1.5},
        {"points": True},
        {"priority": -1},
        {"priority": True},
        {"explanation": "x" * (MAX_SCORE_EXPLANATION_LENGTH + 1)},
        {"explanation": "unsafe\ntext"},
    ],
)
def test_invalid_factor_fails_fast(overrides):
    values = {
        "id": "match.test",
        "category": ScoreCategory.MATCH_QUALITY,
        "points": 5,
        "explanation": "Valid explanation.",
        "priority": 10,
    }
    values.update(overrides)
    with pytest.raises(ValueError):
        ScoreFactor(**values)


def test_context_is_immutable_and_rejects_malformed_values():
    context = OpportunityScoringContext(
        career_goal_matches=(ScoringContextMatch("Television"),),
        dream_target_matches=(ScoringContextMatch("Test Procedural"),),
        watchlist_matches=("Detective",),
        requested_archetypes=("Authority Figure",),
        submission_status="Passed",
        feedback_type="Interesting Stretch",
        audition_travel_limit_hours=2.0,
    )
    with pytest.raises(FrozenInstanceError):
        context.feedback_type = "Not My Type"
    with pytest.raises(ValueError):
        OpportunityScoringContext(career_goal_matches=["Television"])
    with pytest.raises(ValueError):
        OpportunityScoringContext(watchlist_matches=("",))
    with pytest.raises(ValueError):
        OpportunityScoringContext(feedback_type="invented")
    with pytest.raises(ValueError):
        OpportunityScoringContext(audition_travel_limit_hours=float("inf"))


def test_result_and_nested_contracts_are_immutable():
    result = build_opportunity_score(opportunity_id="fixed", factors=[factor()])
    with pytest.raises(FrozenInstanceError):
        result.overall_score = 1
    with pytest.raises(FrozenInstanceError):
        result.categories[0].raw_subtotal = 99
    with pytest.raises(FrozenInstanceError):
        result.confidence.level = "High"


def test_baseline_only_result_has_all_empty_categories_in_approved_order():
    result = build_opportunity_score(opportunity_id="fixed")
    assert result.overall_score == 50
    assert result.hard_override is False
    assert result.hard_override_reason is None
    assert tuple(category.category for category in result.categories) == SCORE_CATEGORY_ORDER
    assert all(
        category.raw_subtotal == category.capped_subtotal == 0 for category in result.categories
    )
    assert all(category.factors == () for category in result.categories)
    assert result.positive_contributors == ()
    assert result.negative_contributors == ()


def test_category_aggregation_caps_positive_negative_and_mixed_subtotals():
    result = build_opportunity_score(
        opportunity_id="fixed",
        factors=[
            factor("match.positive", points=50),
            factor("career.negative", ScoreCategory.CAREER_VALUE, -30),
            factor("practical.positive", ScoreCategory.PRACTICALITY, 14),
            factor("practical.negative", ScoreCategory.PRACTICALITY, -6, 20),
        ],
    )
    categories = {category.category: category for category in result.categories}
    assert (
        categories[ScoreCategory.MATCH_QUALITY].raw_subtotal,
        categories[ScoreCategory.MATCH_QUALITY].capped_subtotal,
    ) == (50, 30)
    assert (
        categories[ScoreCategory.CAREER_VALUE].raw_subtotal,
        categories[ScoreCategory.CAREER_VALUE].capped_subtotal,
    ) == (-30, -10)
    assert (
        categories[ScoreCategory.PRACTICALITY].raw_subtotal,
        categories[ScoreCategory.PRACTICALITY].capped_subtotal,
    ) == (8, 8)
    assert result.overall_score == 78


def test_final_normalization_clamps_above_one_hundred_after_category_caps():
    result = build_opportunity_score(
        opportunity_id="fixed",
        factors=[
            factor(f"positive.{index}", category, 100, index)
            for index, category in enumerate(SCORE_CATEGORY_ORDER)
        ],
    )
    assert result.overall_score == 100
    assert all(category.raw_subtotal == 100 for category in result.categories)


def test_final_normalization_clamps_below_zero_after_category_caps():
    result = build_opportunity_score(
        opportunity_id="fixed",
        factors=[
            factor(f"negative.{index}", category, -100, index)
            for index, category in enumerate(SCORE_CATEGORY_ORDER)
        ],
    )
    assert result.overall_score == 0


def test_duplicate_factor_ids_fail_fast():
    with pytest.raises(ValueError, match="factor ids must be unique"):
        build_opportunity_score(
            opportunity_id="fixed",
            factors=[factor("same.id"), factor("same.id", points=-2)],
        )


def test_factor_and_contributor_order_is_independent_of_input_order():
    factors = [
        factor("career.tie-b", ScoreCategory.CAREER_VALUE, 8, 20),
        factor("match.zero", ScoreCategory.MATCH_QUALITY, 0, 1),
        factor("career.tie-a", ScoreCategory.CAREER_VALUE, 8, 20),
        factor("confidence.negative-b", ScoreCategory.CONFIDENCE, -7, 30),
        factor("confidence.negative-a", ScoreCategory.CONFIDENCE, -7, 30),
        factor("interest.small", ScoreCategory.ACTOR_INTEREST, 2, 1),
        factor("practical.large", ScoreCategory.PRACTICALITY, 10, 50),
    ]
    forward = build_opportunity_score(opportunity_id="fixed", factors=factors)
    reverse = build_opportunity_score(opportunity_id="fixed", factors=reversed(factors))
    assert forward == reverse
    assert serialized(forward) == serialized(reverse)
    assert [item.id for item in forward.positive_contributors] == [
        "practical.large",
        "career.tie-a",
        "career.tie-b",
    ]
    assert [item.id for item in forward.negative_contributors] == [
        "confidence.negative-a",
        "confidence.negative-b",
    ]
    assert all(item.points != 0 for item in forward.positive_contributors)


def test_contributor_limits_select_highest_magnitudes():
    values = [factor(f"positive.{index}", points=index + 1) for index in range(5)]
    values.extend(factor(f"negative.{index}", points=-(index + 1)) for index in range(5))
    result = build_opportunity_score(opportunity_id="fixed", factors=values)
    assert [value.points for value in result.positive_contributors] == [5, 4, 3]
    assert [value.points for value in result.negative_contributors] == [-5, -4, -3]


def test_exact_serialization_contract_is_stable():
    result = build_opportunity_score(opportunity_id="fixed")
    assert result.as_dict() == {
        "opportunity_id": "fixed",
        "scoring_version": 1,
        "overall_score": 50,
        "baseline_score": 50,
        "categories": [
            {
                "category": category.value,
                "raw_subtotal": 0,
                "capped_subtotal": 0,
                "factors": [],
            }
            for category in SCORE_CATEGORY_ORDER
        ],
        "positive_contributors": [],
        "negative_contributors": [],
        "hard_override": False,
        "hard_override_reason": None,
        "confidence": {
            "level": "Not Scored",
            "summary": "Detailed confidence factors are not implemented in the version 1 scoring foundation.",
        },
        "explanation": {
            "summary": "No detailed scoring factors apply yet; the score remains at the baseline."
        },
    }


@pytest.mark.parametrize(
    ("overrides", "expected_reason"),
    [
        ({"hidden_by_rule": "user_rejected"}, "user_rejected"),
        ({"source_metadata": {"date_validation": {"status": "Expired"}}}, "deadline_expired"),
        ({"breakdown_classification": "Crew Job"}, "classification_rejected"),
        ({"demographic_match_status": "Not a Match"}, "demographic_incompatible"),
        ({"hidden_by_rule": "dealbreaker_role_type"}, "excluded_role_type"),
        ({"hidden_by_rule": "dealbreaker_availability"}, "availability_conflict"),
        ({"hidden_by_rule": "dealbreaker_audition_travel"}, "hard_travel_limit"),
        ({"visibility_status": "discarded"}, "discarded"),
    ],
)
def test_proven_hard_overrides_return_zero_without_mutation(overrides, expected_reason):
    item = opportunity(**overrides)
    before = opportunity_snapshot(item)
    result = OpportunityIntelligenceService(MagicMock()).score(
        item,
        actor_profile(),
        OpportunityScoringContext(),
        as_of=fixed_as_of(),
    )
    assert result.overall_score == 0
    assert result.hard_override is True
    assert result.hard_override_reason == expected_reason
    assert result.explanation.summary
    assert opportunity_snapshot(item) == before


def test_hard_override_order_is_stable_when_multiple_states_apply():
    assert HARD_OVERRIDE_REASON_ORDER[0] == "user_rejected"
    item = opportunity(
        hidden_by_rule="user_rejected",
        visibility_status="discarded",
        breakdown_classification="Crew Job",
    )
    result = OpportunityIntelligenceService(None).score(
        item,
        actor_profile(),
        OpportunityScoringContext(),
        as_of=fixed_as_of(),
    )
    assert result.hard_override_reason == "user_rejected"


@pytest.mark.parametrize(
    "overrides",
    [
        {"visibility_status": "hidden"},
        {"visibility_status": "travel_exception", "hidden_by_rule": "travel_exception"},
        {"source_metadata": {"breakdown_parse_confidence": 20}},
        {"source_metadata": {"trust_verification": {"status": "Blocked"}}},
        {"is_duplicate": True},
        {"union": "Unknown"},
        {"audition_type": "In-Person", "audition_travel_hours": None},
    ],
)
def test_uncertain_or_informational_state_does_not_invent_hard_override(overrides):
    result = OpportunityIntelligenceService(None).score(
        opportunity(**overrides),
        actor_profile(),
        OpportunityScoringContext(),
        as_of=fixed_as_of(),
    )
    assert result.overall_score > 0
    assert result.hard_override is False


def test_mixed_per_role_demographic_results_do_not_invent_hard_override():
    result = OpportunityIntelligenceService(None).score(
        opportunity(
            demographic_match_status="Not a Match",
            demographic_match_details={
                "role_results": [
                    {"role_name": "Role A", "status": "Not a Match"},
                    {"role_name": "Role B", "status": "Match"},
                ]
            },
        ),
        actor_profile(),
        OpportunityScoringContext(),
        as_of=fixed_as_of(),
    )
    assert result.hard_override is False
    assert result.overall_score > 0


def test_aware_utc_and_non_utc_equivalent_instants_produce_same_result():
    item = opportunity()
    service = OpportunityIntelligenceService(None)
    utc = fixed_as_of()
    non_utc = utc.astimezone(timezone(timedelta(hours=-4)))
    first = service.score(item, actor_profile(), OpportunityScoringContext(), as_of=utc)
    second = service.score(item, actor_profile(), OpportunityScoringContext(), as_of=non_utc)
    assert first == second
    assert serialized(first) == serialized(second)


def test_naive_as_of_is_rejected():
    with pytest.raises(ValueError, match="as_of must be timezone-aware"):
        OpportunityIntelligenceService(None).score(
            opportunity(),
            actor_profile(),
            OpportunityScoringContext(),
            as_of=datetime(2026, 8, 2, 12, 0),
        )

    with pytest.raises(ValueError, match="as_of must be timezone-aware"):
        OpportunityIntelligenceService(None).score(
            opportunity(),
            actor_profile(),
            OpportunityScoringContext(),
            as_of="2026-08-02T12:00:00Z",
        )


def test_score_is_repeatable_has_no_wall_clock_dependency_and_never_uses_session():
    item = opportunity(urgency_score=17, quality_score=29)
    actor = actor_profile()
    context = OpportunityScoringContext()
    database = MagicMock()
    service = OpportunityIntelligenceService(database)
    opportunity_before = opportunity_snapshot(item)
    actor_before = deepcopy(
        {
            attribute.key: getattr(actor, attribute.key)
            for attribute in actor.__mapper__.column_attrs
        }
    )

    with (
        patch("app.services.opportunity_intelligence_service.datetime") as clock,
        patch("app.agents.strategy_agent.StrategyAgent.analyze") as strategy,
    ):
        results = [service.score(item, actor, context, as_of=fixed_as_of()) for _ in range(3)]

    assert results[0] == results[1] == results[2]
    assert serialized(results[0]) == serialized(results[1]) == serialized(results[2])
    assert opportunity_snapshot(item) == opportunity_before
    assert {
        attribute.key: getattr(actor, attribute.key) for attribute in actor.__mapper__.column_attrs
    } == actor_before
    assert item.urgency_score == 17
    assert item.quality_score == 29
    assert item.recommendations == []
    assert not clock.called
    strategy.assert_not_called()
    database.assert_not_called()
    assert database.method_calls == []
