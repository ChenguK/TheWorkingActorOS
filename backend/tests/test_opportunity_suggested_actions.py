from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import timedelta, timezone

import pytest

from app.services.opportunity_intelligence_service import OpportunityIntelligenceService
from app.services.opportunity_score import (
    OpportunityActionContext,
    OpportunityScoringContext,
    ScoreCategory,
    ScoreFactor,
    SuggestedAction,
    build_opportunity_score,
    suggest_opportunity_action,
)
from tests.intelligence_builders import (
    actor_profile,
    fixed_as_of,
    opportunity,
    opportunity_snapshot,
    parsed_role,
)


TRACKED_STATUSES = (
    "Submitted",
    "Requested",
    "Self-Tape Callback",
    "In-Person Callback",
    "Pinned",
    "Booked",
    "Passed",
    "No Response",
)


def controlled_score(
    total: int,
    *,
    deadline_factor: str | None = None,
    stretch: bool = False,
    confidence_points: int | None = 0,
    hard_override_reason: str | None = None,
):
    if hard_override_reason:
        return build_opportunity_score(
            opportunity_id="controlled",
            hard_override_reason=hard_override_reason,
        )

    factors = []
    remaining = total - 50
    confidence_contribution = confidence_points or 0
    remaining -= confidence_contribution
    match_points = min(30, max(-35, remaining))
    career_points = remaining - match_points
    if stretch:
        factors.append(
            ScoreFactor(
                "match.role_fit.stretch",
                ScoreCategory.MATCH_QUALITY,
                0,
                "Controlled Stretch Fit marker.",
                10,
            )
        )
    if match_points:
        factors.append(
            ScoreFactor(
                "match.controlled.total",
                ScoreCategory.MATCH_QUALITY,
                match_points,
                "Controlled score contribution.",
                20,
            )
        )
    if career_points:
        factors.append(
            ScoreFactor(
                "career.controlled.total",
                ScoreCategory.CAREER_VALUE,
                career_points,
                "Controlled score contribution.",
                100,
            )
        )
    if deadline_factor:
        factors.append(
            ScoreFactor(
                deadline_factor,
                ScoreCategory.PRACTICALITY,
                0,
                "Controlled deadline marker.",
                240,
            )
        )
    if confidence_points is not None:
        factors.append(
            ScoreFactor(
                "confidence.controlled",
                ScoreCategory.CONFIDENCE,
                confidence_points,
                "Controlled confidence contribution.",
                300,
            )
        )
    result = build_opportunity_score(opportunity_id="controlled", factors=factors)
    assert result.overall_score == total
    return result


def action(score, **overrides):
    values = {
        "is_duplicate": False,
        "visibility_status": "visible",
        "submission_status": None,
    }
    values.update(overrides)
    return suggest_opportunity_action(score, OpportunityActionContext(**values))


def assert_action(result, expected, reason):
    assert result.action is expected
    assert result.reason_code == reason
    assert result.explanation


def test_action_enum_has_only_the_approved_values():
    assert tuple(value.value for value in SuggestedAction) == (
        "ignore",
        "save_for_later",
        "good_stretch_role",
        "apply_now",
        "review_today",
        "low_priority",
    )


def test_every_direct_action_and_reason():
    assert_action(
        action(controlled_score(0, hard_override_reason="user_rejected")),
        SuggestedAction.IGNORE,
        "hard_override",
    )
    assert_action(
        action(controlled_score(80), is_duplicate=True),
        SuggestedAction.IGNORE,
        "duplicate_opportunity",
    )
    assert_action(
        action(controlled_score(80), submission_status="Submitted"),
        SuggestedAction.SAVE_FOR_LATER,
        "already_tracked",
    )
    assert_action(
        action(controlled_score(65, stretch=True)),
        SuggestedAction.GOOD_STRETCH_ROLE,
        "strategic_stretch",
    )
    assert_action(
        action(controlled_score(85, deadline_factor="practicality.deadline.within_7d")),
        SuggestedAction.APPLY_NOW,
        "high_priority_actionable",
    )
    assert_action(
        action(controlled_score(70)),
        SuggestedAction.REVIEW_TODAY,
        "strong_score_review",
    )
    assert_action(
        action(controlled_score(54, deadline_factor="practicality.deadline.within_72h")),
        SuggestedAction.REVIEW_TODAY,
        "urgent_deadline_review",
    )
    for deadline in ("practicality.deadline.missing", "practicality.deadline.distant"):
        assert_action(
            action(controlled_score(55, deadline_factor=deadline)),
            SuggestedAction.SAVE_FOR_LATER,
            "promising_not_urgent",
        )
    assert_action(
        action(controlled_score(54)),
        SuggestedAction.LOW_PRIORITY,
        "limited_current_value",
    )


@pytest.mark.parametrize(
    ("score_value", "stretch", "deadline", "expected"),
    [
        (54, False, "practicality.deadline.missing", SuggestedAction.LOW_PRIORITY),
        (55, False, "practicality.deadline.missing", SuggestedAction.SAVE_FOR_LATER),
        (64, True, None, SuggestedAction.LOW_PRIORITY),
        (65, True, None, SuggestedAction.GOOD_STRETCH_ROLE),
        (69, False, None, SuggestedAction.LOW_PRIORITY),
        (70, False, None, SuggestedAction.REVIEW_TODAY),
        (84, False, "practicality.deadline.within_7d", SuggestedAction.REVIEW_TODAY),
        (85, False, "practicality.deadline.within_7d", SuggestedAction.APPLY_NOW),
    ],
)
def test_inclusive_score_thresholds(score_value, stretch, deadline, expected):
    assert (
        action(controlled_score(score_value, stretch=stretch, deadline_factor=deadline)).action
        is expected
    )


@pytest.mark.parametrize(
    ("deadline_factor", "score_value", "expected"),
    [
        ("practicality.deadline.within_72h", 54, SuggestedAction.REVIEW_TODAY),
        ("practicality.deadline.within_7d", 54, SuggestedAction.LOW_PRIORITY),
        ("practicality.deadline.within_7d", 85, SuggestedAction.APPLY_NOW),
        ("practicality.deadline.distant", 85, SuggestedAction.REVIEW_TODAY),
        ("practicality.deadline.missing", 69, SuggestedAction.SAVE_FOR_LATER),
    ],
)
def test_action_uses_task_four_deadline_bands(deadline_factor, score_value, expected):
    assert action(controlled_score(score_value, deadline_factor=deadline_factor)).action is expected


def test_expired_deadline_remains_hard_override():
    result = OpportunityIntelligenceService(None).score(
        opportunity(source_metadata={"date_validation": {"status": "Expired"}}),
        actor_profile(),
        OpportunityScoringContext(),
        as_of=fixed_as_of(),
    )
    assert_action(result.suggested_action, SuggestedAction.IGNORE, "hard_override")


def test_equivalent_timezone_inputs_produce_the_same_action():
    deadline = fixed_as_of().replace(hour=15)
    item = opportunity(submission_deadline=deadline)
    service = OpportunityIntelligenceService(None)
    first = service.score(item, actor_profile(), OpportunityScoringContext(), as_of=fixed_as_of())
    second = service.score(
        item,
        actor_profile(),
        OpportunityScoringContext(),
        as_of=fixed_as_of().astimezone(timezone(timedelta(hours=-4))),
    )
    assert first.suggested_action == second.suggested_action


def test_first_match_precedence_is_stable():
    strongest = controlled_score(
        100,
        deadline_factor="practicality.deadline.within_24h",
        stretch=True,
        hard_override_reason="user_rejected",
    )
    assert (
        action(strongest, is_duplicate=True, submission_status="Booked").reason_code
        == "hard_override"
    )

    candidate = controlled_score(
        100, deadline_factor="practicality.deadline.within_24h", stretch=True
    )
    assert (
        action(candidate, is_duplicate=True, submission_status="Booked").reason_code
        == "duplicate_opportunity"
    )
    assert action(candidate, submission_status="Booked").reason_code == "already_tracked"
    assert action(candidate).reason_code == "strategic_stretch"

    apply = controlled_score(85, deadline_factor="practicality.deadline.within_72h")
    assert action(apply).reason_code == "high_priority_actionable"
    assert (
        action(controlled_score(70, deadline_factor="practicality.deadline.missing")).reason_code
        == "strong_score_review"
    )


@pytest.mark.parametrize("status", TRACKED_STATUSES)
def test_every_persisted_submission_status_is_already_tracked(status):
    result = action(
        controlled_score(100, deadline_factor="practicality.deadline.within_24h"),
        submission_status=status,
    )
    assert_action(result, SuggestedAction.SAVE_FOR_LATER, "already_tracked")


def test_missing_submission_is_neutral_and_unsupported_status_is_rejected():
    assert action(controlled_score(54)).reason_code == "limited_current_value"
    with pytest.raises(ValueError, match="unsupported"):
        OpportunityActionContext(submission_status="Tracked")


def test_duplicate_is_explicit_and_beats_tracked_but_not_hard_override():
    regular = controlled_score(80)
    assert action(regular, is_duplicate=False).reason_code == "strong_score_review"
    assert (
        action(regular, is_duplicate=True, submission_status="Submitted").reason_code
        == "duplicate_opportunity"
    )
    hard = controlled_score(0, hard_override_reason="discarded")
    assert action(hard, is_duplicate=True).reason_code == "hard_override"


def test_duplicate_is_not_inferred_from_titles_or_roles():
    item = opportunity(project="Duplicate", role="Duplicate")
    result = OpportunityIntelligenceService(None).score(
        item,
        actor_profile(),
        OpportunityScoringContext(),
        as_of=fixed_as_of(),
    )
    assert result.suggested_action.reason_code != "duplicate_opportunity"


def test_only_deterministic_best_fit_can_trigger_stretch_action():
    service = OpportunityIntelligenceService(None)
    context = OpportunityScoringContext()
    secondary_stretch = opportunity(
        breakdown_roles=[
            parsed_role(role_name="Lead", fit_status="Strong Fit"),
            parsed_role(role_name="Other", fit_status="Stretch Fit"),
        ]
    )
    result = service.score(secondary_stretch, actor_profile(), context, as_of=fixed_as_of())
    assert result.overall_score >= 65
    assert result.suggested_action.action is not SuggestedAction.GOOD_STRETCH_ROLE


@pytest.mark.parametrize("visibility", ["hidden", "travel_exception"])
def test_reviewable_nonvisible_states_cannot_apply_now(visibility):
    result = action(
        controlled_score(85, deadline_factor="practicality.deadline.within_7d"),
        visibility_status=visibility,
    )
    assert_action(result, SuggestedAction.REVIEW_TODAY, "strong_score_review")


def test_low_confidence_blocks_apply_now_but_medium_allows_it():
    low = controlled_score(
        85, deadline_factor="practicality.deadline.within_7d", confidence_points=-1
    )
    medium = controlled_score(
        85, deadline_factor="practicality.deadline.within_7d", confidence_points=0
    )
    assert action(low).action is SuggestedAction.REVIEW_TODAY
    assert action(medium).action is SuggestedAction.APPLY_NOW


def test_action_serialization_and_immutability_are_stable():
    result = action(controlled_score(85, deadline_factor="practicality.deadline.within_7d"))
    assert result.as_dict() == {
        "action": "apply_now",
        "reason_code": "high_priority_actionable",
        "explanation": "This visible opportunity has a high score, sufficient confidence, and a near deadline.",
    }
    with pytest.raises(FrozenInstanceError):
        result.reason_code = "changed"


def test_service_action_selection_is_read_only_and_does_not_change_score_inputs():
    item = opportunity()
    actor = actor_profile()
    context = OpportunityScoringContext(submission_status="Requested")
    item_before = opportunity_snapshot(item)
    actor_before = {
        attribute.key: deepcopy(getattr(actor, attribute.key))
        for attribute in actor.__mapper__.column_attrs
    }
    context_before = deepcopy(context)
    service = OpportunityIntelligenceService(None)
    first = service.score(item, actor, context, as_of=fixed_as_of())
    second = service.score(item, actor, context, as_of=fixed_as_of())
    assert first.as_dict() == second.as_dict()
    assert first.suggested_action.reason_code == "already_tracked"
    assert opportunity_snapshot(item) == item_before
    assert {
        attribute.key: deepcopy(getattr(actor, attribute.key))
        for attribute in actor.__mapper__.column_attrs
    } == actor_before
    assert context == context_before
