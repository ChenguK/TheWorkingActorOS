from __future__ import annotations

from copy import deepcopy
import json
from unittest.mock import MagicMock, patch

import pytest

from app.services.opportunity_intelligence_service import OpportunityIntelligenceService
from app.services.opportunity_score import (
    OPPORTUNITY_SCORE_BASELINE,
    OpportunityScoringContext,
    ScoreCategory,
    ScoreFactor,
    ScoringContextMatch,
    build_opportunity_score,
)
from tests.intelligence_builders import (
    actor_profile,
    fixed_as_of,
    opportunity,
    opportunity_snapshot,
    parsed_role,
)


def neutral_actor(**overrides):
    values = {
        "sag_status": "Unknown",
        "union_status": "Unknown",
        "languages": [],
        "included_role_types": [],
    }
    values.update(overrides)
    return actor_profile(**values)


def neutral_opportunity(**overrides):
    values = {
        "role_type": None,
        "union": "Unknown",
        "demographic_match_status": "Needs Review",
        "breakdown_roles": [],
    }
    values.update(overrides)
    return opportunity(**values)


def score(item=None, actor=None, context=None, database=None):
    return OpportunityIntelligenceService(database).score(
        item or neutral_opportunity(),
        actor or neutral_actor(),
        context or OpportunityScoringContext(),
        as_of=fixed_as_of(),
    )


def factor_ids(result):
    return [factor.id for category in result.categories for factor in category.factors]


def match_category(result):
    return next(
        category
        for category in result.categories
        if category.category is ScoreCategory.MATCH_QUALITY
    )


def career_category(result):
    return next(
        category
        for category in result.categories
        if category.category is ScoreCategory.CAREER_VALUE
    )


@pytest.mark.parametrize(
    ("fit_status", "expected_id", "points", "explanation", "overall"),
    [
        (
            "Strong Fit",
            "match.role_fit.strong",
            18,
            "Strong Fit is the best parsed role fit (+18).",
            68,
        ),
        (
            "strong fit",
            "match.role_fit.strong",
            18,
            "Strong Fit is the best parsed role fit (+18).",
            68,
        ),
        (
            "Possible Fit",
            "match.role_fit.possible",
            10,
            "Possible Fit is the best parsed role fit (+10).",
            60,
        ),
        (
            "Stretch Fit",
            "match.role_fit.stretch",
            6,
            "Stretch Fit is the best parsed role fit (+6).",
            56,
        ),
        (
            "Not Fit",
            "match.role_fit.none",
            -25,
            "Parsed roles exist, but none currently fit (-25).",
            25,
        ),
    ],
)
def test_exact_best_role_fit_factor(fit_status, expected_id, points, explanation, overall):
    result = score(neutral_opportunity(breakdown_roles=[parsed_role(fit_status=fit_status)]))
    category = match_category(result)
    assert category.raw_subtotal == category.capped_subtotal == points
    assert result.overall_score == overall
    assert category.factors == (
        ScoreFactor(
            id=expected_id,
            category=ScoreCategory.MATCH_QUALITY,
            points=points,
            explanation=explanation,
            priority=10,
        ),
    )


@pytest.mark.parametrize("fit_status", ["Needs Review", "needs review", "Unsupported", None])
def test_review_unknown_and_missing_fit_values_are_neutral(fit_status):
    roles = [] if fit_status is None else [parsed_role(fit_status=fit_status)]
    result = score(neutral_opportunity(breakdown_roles=roles))
    assert result.overall_score == OPPORTUNITY_SCORE_BASELINE
    assert match_category(result).factors == ()


def test_best_role_fit_uses_precedence_not_relationship_order_or_repetition():
    roles = [
        parsed_role(role_name="Role Z", fit_status="Not Fit"),
        parsed_role(role_name="Role B", fit_status="Stretch Fit"),
        parsed_role(role_name="Role A", fit_status="Strong Fit"),
        parsed_role(role_name="Role A", fit_status="Strong Fit"),
        parsed_role(role_name="Role C", fit_status="Possible Fit"),
    ]
    forward = score(neutral_opportunity(breakdown_roles=roles))
    reverse = score(neutral_opportunity(breakdown_roles=list(reversed(roles))))
    assert forward.as_dict() == reverse.as_dict()
    assert factor_ids(forward) == ["match.role_fit.strong"]


def test_needs_review_prevents_not_fit_penalty_when_outcome_is_unresolved():
    result = score(
        neutral_opportunity(
            breakdown_roles=[
                parsed_role(role_name="Role A", fit_status="Not Fit"),
                parsed_role(role_name="Role B", fit_status="Needs Review"),
            ]
        )
    )
    assert result.overall_score == 50
    assert match_category(result).factors == ()


def test_unknown_fit_prevents_not_fit_penalty_when_outcome_is_unresolved():
    result = score(
        neutral_opportunity(
            breakdown_roles=[
                parsed_role(role_name="Role A", fit_status="Not Fit"),
                parsed_role(role_name="Role B", fit_status="Unsupported"),
            ]
        )
    )
    assert result.overall_score == 50
    assert match_category(result).factors == ()


def test_confirmed_demographic_match_emits_one_factor():
    result = score(neutral_opportunity(demographic_match_status="Match"))
    assert match_category(result).factors == (
        ScoreFactor(
            id="match.demographic.confirmed",
            category=ScoreCategory.MATCH_QUALITY,
            points=8,
            explanation="Existing demographic matching confirms actor and role overlap (+8).",
            priority=20,
        ),
    )
    assert result.overall_score == 58


@pytest.mark.parametrize("status", ["Needs Review", None])
def test_review_or_missing_demographic_state_is_neutral(status):
    item = neutral_opportunity()
    item.demographic_match_status = status
    assert factor_ids(score(item)) == []


def test_proven_demographic_mismatch_remains_a_hard_override_without_factors():
    result = score(neutral_opportunity(demographic_match_status="Not a Match"))
    assert result.overall_score == 0
    assert result.hard_override_reason == "demographic_incompatible"
    assert factor_ids(result) == []


def test_mixed_role_demographic_results_remain_reviewable():
    result = score(
        neutral_opportunity(
            demographic_match_status="Not a Match",
            demographic_match_details={
                "role_results": [
                    {"role_name": "A", "status": "Not a Match"},
                    {"role_name": "B", "status": "Match"},
                ]
            },
        )
    )
    assert result.hard_override is False
    assert "match.demographic.confirmed" not in factor_ids(result)


def test_explicit_preferred_role_type_emits_one_factor_with_alias_normalization():
    result = score(
        neutral_opportunity(
            role_type="Co-Star",
            breakdown_roles=[parsed_role(role_type="costar", fit_status="Needs Review")],
        ),
        neutral_actor(included_role_types=["Co Star", "co-star", "CO STAR"]),
    )
    assert factor_ids(result) == ["match.role_type.preferred"]
    assert match_category(result).factors[0].points == 4
    assert match_category(result).factors[0].priority == 30


@pytest.mark.parametrize(
    ("role_type", "preferences"),
    [(None, ["Guest Star"]), ("Guest Star", []), ("Unknown", ["Guest Star"])],
)
def test_unknown_or_unconfigured_role_type_preference_is_neutral(role_type, preferences):
    result = score(
        neutral_opportunity(role_type=role_type),
        neutral_actor(included_role_types=preferences),
    )
    assert "match.role_type.preferred" not in factor_ids(result)


def test_existing_excluded_role_type_decision_remains_hard_override():
    result = score(neutral_opportunity(hidden_by_rule="dealbreaker_role_type"))
    assert result.overall_score == 0
    assert result.hard_override_reason == "excluded_role_type"


@pytest.mark.parametrize(
    ("requirement", "languages", "expected_id", "expected_points"),
    [
        ("English", ["English"], "match.language.required_met", 4),
        (
            "Must speak English and Spanish",
            ["English", "Spanish"],
            "match.language.required_met",
            4,
        ),
        ("SPANISH, spanish", ["Spanish"], "match.language.required_met", 4),
        ("Spanish", ["English"], "match.language.required_missing", -8),
        ("English and Spanish", ["English"], "match.language.required_missing", -8),
        ("English and Spanish", [], "match.language.required_missing", -8),
    ],
)
def test_explicit_language_requirements_emit_one_bounded_factor(
    requirement, languages, expected_id, expected_points
):
    item = neutral_opportunity(
        breakdown_roles=[parsed_role(fit_status="Needs Review", language_requirements=requirement)]
    )
    result = score(item, neutral_actor(languages=languages))
    language_factors = [
        value for value in match_category(result).factors if value.id.startswith("match.language")
    ]
    assert len(language_factors) == 1
    assert language_factors[0].id == expected_id
    assert language_factors[0].points == expected_points
    assert language_factors[0].priority == 40


@pytest.mark.parametrize(
    "requirement",
    [None, "", "Spanish preferred", "French is a plus", "Klingon required"],
)
def test_missing_ambiguous_or_unrecognized_language_requirement_is_neutral(requirement):
    item = neutral_opportunity(
        breakdown_roles=[parsed_role(fit_status="Needs Review", language_requirements=requirement)]
    )
    assert not any(value.startswith("match.language") for value in factor_ids(score(item)))


def test_language_is_taken_from_best_fit_role_only():
    result = score(
        neutral_opportunity(
            breakdown_roles=[
                parsed_role(
                    role_name="Matching Role",
                    fit_status="Strong Fit",
                    language_requirements="English",
                ),
                parsed_role(
                    role_name="Other Role", fit_status="Not Fit", language_requirements="Spanish"
                ),
            ]
        ),
        neutral_actor(languages=["English"]),
    )
    assert "match.language.required_met" in factor_ids(result)
    assert "match.language.required_missing" not in factor_ids(result)


@pytest.mark.parametrize(
    ("actor_union", "role_union"),
    [
        ("SAG-AFTRA", "SAG"),
        ("AEA", "Equity"),
        ("Non-Union", "non union"),
        ("Union", "Union"),
        ("Both", "SAG-AFTRA"),
        ("Union and Non-Union", "Non-Union"),
    ],
)
def test_explicit_union_compatibility_emits_one_factor(actor_union, role_union):
    result = score(
        neutral_opportunity(union=role_union),
        neutral_actor(union_status=actor_union, sag_status="Unknown"),
    )
    union_factor = match_category(result).factors[0]
    assert union_factor.id == "match.union.compatible"
    assert union_factor.points == 3
    assert union_factor.priority == 50


def test_known_sag_status_is_used_when_general_union_status_is_unknown():
    result = score(
        neutral_opportunity(union="SAG-AFTRA"),
        neutral_actor(union_status="Unknown", sag_status="SAG-AFTRA"),
    )
    assert "match.union.compatible" in factor_ids(result)


@pytest.mark.parametrize(
    ("actor_union", "role_union"),
    [
        ("Unknown", "SAG-AFTRA"),
        ("SAG Eligible", "SAG-AFTRA"),
        ("SAG-AFTRA", "Unknown"),
        ("SAG-AFTRA", "AEA"),
        ("Non-Union", "SAG-AFTRA"),
        ("", ""),
    ],
)
def test_union_uncertainty_or_incompatibility_is_neutral(actor_union, role_union):
    result = score(
        neutral_opportunity(union=role_union),
        neutral_actor(union_status=actor_union, sag_status="Unknown"),
    )
    assert "match.union.compatible" not in factor_ids(result)
    assert result.hard_override is False


def test_active_goal_selects_one_deterministic_safe_label():
    context = OpportunityScoringContext(
        career_goal_matches=(
            ScoringContextMatch("Streaming Guest Star"),
            ScoringContextMatch("Film Lead"),
            ScoringContextMatch("film lead"),
            ScoringContextMatch("Inactive Goal", active=False),
        )
    )
    result = score(context=context)
    assert career_category(result).factors == (
        ScoreFactor(
            id="career.goal.active_match",
            category=ScoreCategory.CAREER_VALUE,
            points=8,
            explanation="Active career goal explicitly matches: Film Lead (+8).",
            priority=100,
        ),
    )


def test_dream_target_selects_one_deterministic_active_target():
    context = OpportunityScoringContext(
        dream_target_matches=(
            ScoringContextMatch("Studio Drama"),
            ScoringContextMatch("Casting Office A"),
            ScoringContextMatch("Inactive Target", active=False),
        )
    )
    result = score(context=context)
    factor_value = career_category(result).factors[0]
    assert factor_value.id == "career.dream_target.match"
    assert factor_value.points == 7
    assert factor_value.explanation == "Dream target explicitly matches: Casting Office A (+7)."
    assert factor_value.priority == 110


def test_inactive_or_missing_career_matches_are_neutral():
    context = OpportunityScoringContext(
        career_goal_matches=(ScoringContextMatch("Inactive", active=False),),
        dream_target_matches=(ScoringContextMatch("Inactive", active=False),),
    )
    assert career_category(score(context=context)).factors == ()


@pytest.mark.parametrize(
    ("fit", "goals", "archetypes", "expected"),
    [
        ("Stretch Fit", (), ("Authority Figure",), True),
        ("Stretch Fit", (ScoringContextMatch("TV Stretch Goal"),), (), True),
        ("Stretch Fit", (), (), False),
        ("Strong Fit", (ScoringContextMatch("TV Stretch Goal"),), ("Authority Figure",), False),
    ],
)
def test_strategic_stretch_requires_stretch_fit_and_explicit_support(
    fit, goals, archetypes, expected
):
    result = score(
        neutral_opportunity(breakdown_roles=[parsed_role(fit_status=fit)]),
        context=OpportunityScoringContext(
            career_goal_matches=goals,
            stretch_archetype_matches=archetypes,
        ),
    )
    stretch = [
        value for value in career_category(result).factors if value.id == "career.stretch.strategic"
    ]
    assert bool(stretch) is expected
    if stretch:
        assert stretch[0].points == 5
        assert stretch[0].priority == 130


def test_shuffled_and_repeated_context_inputs_serialize_identically():
    item = neutral_opportunity(breakdown_roles=[parsed_role(fit_status="Stretch Fit")])
    first = OpportunityScoringContext(
        career_goal_matches=(ScoringContextMatch("Goal B"), ScoringContextMatch("Goal A")),
        dream_target_matches=(ScoringContextMatch("Target B"), ScoringContextMatch("Target A")),
        stretch_archetype_matches=("Detective", "Authority Figure", "Detective"),
    )
    second = OpportunityScoringContext(
        career_goal_matches=(ScoringContextMatch("Goal A"), ScoringContextMatch("Goal B")),
        dream_target_matches=(ScoringContextMatch("Target A"), ScoringContextMatch("Target B")),
        stretch_archetype_matches=("Authority Figure", "Detective"),
    )
    assert score(item, context=first).as_dict() == score(item, context=second).as_dict()


def test_match_positive_subtotal_caps_at_thirty():
    result = score(
        opportunity(
            demographic_match_status="Match",
            role_type="Guest Star",
            union="SAG-AFTRA",
            breakdown_roles=[
                parsed_role(
                    fit_status="Strong Fit",
                    role_type="Guest Star",
                    language_requirements="English",
                    union_status="SAG-AFTRA",
                )
            ],
        ),
        actor_profile(
            languages=["English"],
            included_role_types=["Guest Star"],
            union_status="SAG-AFTRA",
        ),
    )
    category = match_category(result)
    assert category.raw_subtotal == 37
    assert category.capped_subtotal == 30
    assert result.overall_score == 80


def test_match_negative_cap_and_final_normalization_remain_unchanged():
    result = build_opportunity_score(
        opportunity_id="fixed",
        factors=[
            ScoreFactor(
                id="match.test.negative",
                category=ScoreCategory.MATCH_QUALITY,
                points=-100,
                explanation="Mechanical cap characterization.",
                priority=1,
            )
        ],
    )
    assert match_category(result).raw_subtotal == -100
    assert match_category(result).capped_subtotal == -35
    assert result.overall_score == 15


def test_career_value_combination_reaches_but_does_not_exceed_cap():
    result = score(
        neutral_opportunity(breakdown_roles=[parsed_role(fit_status="Stretch Fit")]),
        context=OpportunityScoringContext(
            career_goal_matches=(ScoringContextMatch("Goal"),),
            dream_target_matches=(ScoringContextMatch("Target"),),
            stretch_archetype_matches=("Detective",),
        ),
    )
    category = career_category(result)
    assert category.raw_subtotal == category.capped_subtotal == 20
    assert result.overall_score == 76


def test_watchlist_context_is_deliberately_deferred_to_actor_interest():
    result = score(context=OpportunityScoringContext(watchlist_matches=("High-priority office",)))
    assert factor_ids(result) == []
    assert result.overall_score == OPPORTUNITY_SCORE_BASELINE


def test_positive_factors_cannot_overcome_existing_hard_override():
    item = opportunity(
        hidden_by_rule="user_rejected",
        demographic_match_status="Match",
        role_type="Guest Star",
        union="SAG-AFTRA",
        breakdown_roles=[parsed_role(fit_status="Strong Fit", language_requirements="English")],
    )
    context = OpportunityScoringContext(
        career_goal_matches=(ScoringContextMatch("Goal"),),
        dream_target_matches=(ScoringContextMatch("Target"),),
        stretch_archetype_matches=("Detective",),
    )
    result = score(item, actor_profile(), context)
    assert result.overall_score == 0
    assert result.hard_override_reason == "user_rejected"
    assert factor_ids(result) == []


def test_fit_and_career_scoring_is_read_only_and_session_independent():
    item = opportunity(
        urgency_score=17,
        quality_score=29,
        breakdown_roles=[parsed_role(fit_status="Strong Fit", language_requirements="English")],
    )
    actor = actor_profile()
    context = OpportunityScoringContext(
        career_goal_matches=(ScoringContextMatch("Television"),),
        dream_target_matches=(ScoringContextMatch("Test Procedural"),),
        stretch_archetype_matches=("Detective",),
    )
    database = MagicMock()
    item_before = opportunity_snapshot(item)
    relationships_before = (
        tuple(item.breakdown_roles),
        tuple(item.recommendations),
        tuple(item.submissions),
    )
    actor_before = deepcopy(
        {
            attribute.key: getattr(actor, attribute.key)
            for attribute in actor.__mapper__.column_attrs
        }
    )
    context_before = deepcopy(context)

    with (
        patch("app.agents.strategy_agent.StrategyAgent.analyze") as strategy,
    ):
        first = OpportunityIntelligenceService(database).score(
            item, actor, context, as_of=fixed_as_of()
        )
        second = OpportunityIntelligenceService(database).score(
            item, actor, context, as_of=fixed_as_of()
        )

    assert first == second
    assert json.dumps(first.as_dict(), sort_keys=False) == json.dumps(
        second.as_dict(), sort_keys=False
    )
    assert opportunity_snapshot(item) == item_before
    assert (
        tuple(item.breakdown_roles),
        tuple(item.recommendations),
        tuple(item.submissions),
    ) == relationships_before
    assert {
        attribute.key: getattr(actor, attribute.key) for attribute in actor.__mapper__.column_attrs
    } == actor_before
    assert context == context_before
    assert item.urgency_score == 17
    assert item.quality_score == 29
    assert database.method_calls == []
    strategy.assert_not_called()
