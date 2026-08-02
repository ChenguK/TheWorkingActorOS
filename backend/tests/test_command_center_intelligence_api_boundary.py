from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
import inspect
import json

import pytest

from app.schemas.agent import ActorCommandCenterRead
from app.services.command_center_service import CommandCenterService
from app.services.opportunity_intelligence_summary import (
    ACTION_LABELS,
    COMMAND_CENTER_INTELLIGENCE_MAX_BYTES,
    serialize_command_center_intelligence,
)
from app.services.opportunity_score import (
    FeedbackScoringEntry,
    OpportunityActionContext,
    OpportunityScoringContext,
    ScoreConfidence,
    ScoringContextMatch,
    SuggestedAction,
    SuggestedActionResult,
    WatchListScoringMatch,
    build_opportunity_score,
    score_opportunity,
    suggest_opportunity_action,
)
from tests.intelligence_builders import (
    actor_profile,
    fixed_as_of,
    opportunity,
    parsed_role,
)


CURRENT_CARD_FIELDS = {
    "id",
    "role",
    "project",
    "original_post_url",
    "priority",
    "urgency_score",
    "quality_score",
    "confidence_level",
    "risk_level",
}
CURRENT_RESPONSE_FIELDS = {
    "today_opportunities",
    "executive_priorities",
    "chief_of_staff_priorities",
    "since_last_visit",
    "upcoming_attention",
    "today_career_recommendation",
    "platform_check_ins",
    "queued_submissions",
    "upcoming_deadlines",
    "outcome_nudges",
    "career_tasks",
    "material_gaps",
    "asset_performance",
}
FORBIDDEN_INTELLIGENCE_FIELDS = {
    "intelligence",
    "intelligence_version",
    "overall_score",
    "suggested_action",
    "action_reason_code",
    "category_scores",
    "categories",
    "factors",
    "positive_contributors",
    "negative_contributors",
    "confidence_summary",
    "hard_override",
    "hard_override_reason",
    "ranking_projection",
    "ranking_position",
    "as_of",
    "scoring_context",
}
REDACTED_EXPLANATION_FACTOR_IDS = {
    "career.goal.active_match",
    "career.dream_target.match",
    "career.stretch.strategic",
    "interest.feedback.fits_me",
    "interest.feedback.interesting_stretch",
    "interest.feedback.save_later",
    "interest.feedback.not_my_type",
}


def _card(index: int = 1) -> dict:
    return {
        "id": f"20000000-0000-0000-0000-{index:012d}",
        "role": f"Detective {index}",
        "project": f"Fictional Procedural {index}",
        "original_post_url": f"https://example.test/casting/{index}",
        "priority": "High",
        "urgency_score": 82,
        "quality_score": 91,
        "confidence_level": "High",
        "risk_level": "Low",
    }


def _response(cards: list[dict]) -> dict:
    return {
        "today_opportunities": cards,
        "executive_priorities": [],
        "chief_of_staff_priorities": [],
        "since_last_visit": [],
        "upcoming_attention": [],
        "today_career_recommendation": None,
        "platform_check_ins": [],
        "queued_submissions": [],
        "upcoming_deadlines": [],
        "outcome_nudges": [],
        "career_tasks": [],
        "material_gaps": [],
        "asset_performance": [],
    }


def _maximum_factor_score():
    actor = actor_profile()
    item = opportunity(
        submission_deadline=fixed_as_of() + timedelta(hours=12),
        travel_covered=True,
        housing_covered=True,
        rate="$1,200/day",
    )
    item.breakdown_roles = [parsed_role(language_requirements="English", fit_status="Strong Fit")]
    context = OpportunityScoringContext(
        career_goal_matches=(ScoringContextMatch("Fictional TV Goal"),),
        dream_target_matches=(ScoringContextMatch("Fictional Procedural"),),
        watchlist_matches=(WatchListScoringMatch("fictional-watch", "High"),),
        feedback_entries=(
            FeedbackScoringEntry(
                "fictional-feedback",
                "This Fits Me",
                fixed_as_of(),
            ),
        ),
        audition_travel_limit_hours=2.0,
    )
    return score_opportunity(item, actor, context, as_of=fixed_as_of())


def _summary(score) -> dict:
    def contributor(factor) -> dict:
        result = {
            "id": factor.id,
            "points": factor.points,
        }
        if factor.id not in REDACTED_EXPLANATION_FACTOR_IDS:
            result["explanation"] = factor.explanation
        return result

    return {
        "version": 1,
        "overall_score": score.overall_score,
        "action": score.suggested_action.action.value,
        "action_reason_code": score.suggested_action.reason_code,
        "confidence": {
            "level": score.confidence.level,
            "summary": score.confidence.summary,
        },
        "hard_override": score.hard_override,
        "hard_override_reason": score.hard_override_reason,
        "top_positive_contributors": [
            contributor(factor) for factor in score.positive_contributors
        ],
        "top_negative_contributors": [
            contributor(factor) for factor in score.negative_contributors
        ],
    }


def _with_intelligence(card: dict, intelligence: dict) -> dict:
    return {**card, "intelligence": intelligence}


def _size(value) -> int:
    return len(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    )


def payload_measurements() -> dict[str, int]:
    maximum = _maximum_factor_score()
    hard_override = build_opportunity_score(
        opportunity_id=_card()["id"],
        hard_override_reason="user_rejected",
    )
    neutral = build_opportunity_score(opportunity_id=_card()["id"])
    one_card = [_card()]
    eight_cards = [_card(index) for index in range(1, 9)]
    return {
        "one_current": _size(_response(one_card)),
        "eight_current": _size(_response(eight_cards)),
        "one_summary": _size(_response([_with_intelligence(_card(), _summary(maximum))])),
        "eight_summary": _size(
            _response([_with_intelligence(card, _summary(maximum)) for card in eight_cards])
        ),
        "one_full": _size(_response([_with_intelligence(_card(), maximum.as_dict())])),
        "eight_full": _size(
            _response([_with_intelligence(card, maximum.as_dict()) for card in eight_cards])
        ),
        "hard_override_full": _size(
            _response([_with_intelligence(_card(), hard_override.as_dict())])
        ),
        "maximum_factor_full": _size(_response([_with_intelligence(_card(), maximum.as_dict())])),
        "neutral_full": _size(_response([_with_intelligence(_card(), neutral.as_dict())])),
    }


def test_current_command_center_schema_and_card_field_sets_are_exact():
    item = opportunity()
    score = build_opportunity_score(opportunity_id=str(item.id))
    card = CommandCenterService(db=None)._opportunity_card(item, score)

    assert set(ActorCommandCenterRead.model_fields) == CURRENT_RESPONSE_FIELDS
    assert set(card) == CURRENT_CARD_FIELDS | {"intelligence"}
    assert set(card) - {"intelligence"} == CURRENT_CARD_FIELDS
    assert card["intelligence"]["version"] == 1


def test_card_projection_uses_completed_score_without_scoring_again():
    source = inspect.getsource(CommandCenterService._opportunity_card)

    assert "serialize_command_center_intelligence(score)" in source
    assert ".score(" not in source
    assert ".as_dict(" not in source


def test_old_response_fixture_remains_valid_and_top_level_extras_are_ignored():
    old_response = _response([_card()])
    validated = ActorCommandCenterRead.model_validate(old_response)
    serialized = validated.model_dump(mode="json")
    assert serialized["today_opportunities"][0].pop("intelligence") is None
    assert serialized == old_response

    with_unknown_top_level = {**old_response, "intelligence_version": 1}
    assert (
        ActorCommandCenterRead.model_validate(with_unknown_top_level).model_dump(mode="json")[
            "today_opportunities"
        ][0]["intelligence"]
        is None
    )


def test_nested_card_dictionary_can_accept_a_future_additive_projection():
    summary = serialize_command_center_intelligence(
        build_opportunity_score(opportunity_id=_card()["id"])
    )
    proposed = _response([_with_intelligence(_card(), summary)])

    validated = ActorCommandCenterRead.model_validate(proposed).model_dump(mode="json")

    assert validated["today_opportunities"][0]["intelligence"] == summary


def test_deterministic_payload_measurements_are_bounded_characterization():
    assert payload_measurements() == {
        "one_current": 571,
        "eight_current": 2363,
        "one_summary": 1193,
        "eight_summary": 7339,
        "one_full": 4927,
        "eight_full": 37211,
        "hard_override_full": 1589,
        "maximum_factor_full": 4927,
        "neutral_full": 1632,
    }


def test_absent_and_evaluated_neutral_are_not_the_same_contract_state():
    neutral = build_opportunity_score(opportunity_id=_card()["id"])
    absent = _with_intelligence(_card(), None)
    evaluated = _with_intelligence(_card(), _summary(neutral))

    assert absent["intelligence"] is None
    assert evaluated["intelligence"]["version"] == 1
    assert evaluated["intelligence"]["overall_score"] == 50
    assert evaluated["intelligence"]["top_positive_contributors"] == []
    assert absent != evaluated


def test_hard_override_summary_exposes_only_bounded_stable_state():
    score = build_opportunity_score(
        opportunity_id=_card()["id"],
        hard_override_reason="user_rejected",
    )
    summary = _summary(score)

    assert summary["overall_score"] == 0
    assert summary["action"] == "ignore"
    assert summary["action_reason_code"] == "hard_override"
    assert summary["hard_override_reason"] == "user_rejected"
    serialized = json.dumps(summary, sort_keys=True)
    for prohibited in (
        "notes",
        "source_metadata",
        "provider_evidence",
        "scoring_context",
        "as_of",
    ):
        assert prohibited not in serialized


@pytest.mark.parametrize(
    "reason",
    [
        "user_rejected",
        "deadline_expired",
        "discarded",
        "demographic_incompatible",
        "excluded_role_type",
        "hard_travel_limit",
    ],
)
def test_proposed_hard_override_contract_uses_only_stable_reason_codes(reason):
    score = build_opportunity_score(
        opportunity_id=_card()["id"],
        hard_override_reason=reason,
    )

    summary = _summary(score)

    assert summary["overall_score"] == 0
    assert summary["action"] == "ignore"
    assert summary["hard_override"] is True
    assert summary["hard_override_reason"] == reason


def test_duplicate_and_tracked_proposals_expose_action_without_workflow_notes():
    base = build_opportunity_score(opportunity_id=_card()["id"])
    duplicate = replace(
        base,
        suggested_action=suggest_opportunity_action(
            base,
            OpportunityActionContext(is_duplicate=True),
        ),
    )
    assert _summary(duplicate)["action_reason_code"] == "duplicate_opportunity"

    for status in (
        "Submitted",
        "Requested",
        "Self-Tape Callback",
        "In-Person Callback",
        "Pinned",
        "Booked",
        "Passed",
        "No Response",
    ):
        tracked = replace(
            base,
            suggested_action=suggest_opportunity_action(
                base,
                OpportunityActionContext(submission_status=status),
            ),
        )
        summary = _summary(tracked)
        assert summary["action"] == "save_for_later"
        assert summary["action_reason_code"] == "already_tracked"
        assert status not in json.dumps(summary)


def test_dynamic_private_explanations_are_redacted_from_summary_proposal():
    score = _maximum_factor_score()
    summary = _summary(score)
    contributors = [
        *summary["top_positive_contributors"],
        *summary["top_negative_contributors"],
    ]

    assert "Fictional TV Goal" not in json.dumps(summary)
    for contributor in contributors:
        if contributor["id"] in REDACTED_EXPLANATION_FACTOR_IDS:
            assert "explanation" not in contributor


def test_production_serializer_is_allowlisted_bounded_and_privacy_safe():
    score = _maximum_factor_score()
    before = score.as_dict()
    summary = serialize_command_center_intelligence(score)
    serialized = json.dumps(summary, sort_keys=True)

    assert set(summary) == {
        "version",
        "overall_score",
        "action",
        "action_label",
        "action_reason_code",
        "confidence",
        "hard_override",
        "hard_override_reason",
        "top_positive_contributors",
        "top_negative_contributors",
    }
    assert len(summary["top_positive_contributors"]) <= 3
    assert len(summary["top_negative_contributors"]) <= 3
    assert _size(summary) == 558
    assert _size([summary] * 8) == 4473
    assert _size(summary) <= COMMAND_CENTER_INTELLIGENCE_MAX_BYTES
    assert score.as_dict() == before
    for sentinel in (
        "Fictional TV Goal",
        "Fictional Procedural",
        "fictional-watch",
        "fictional-feedback",
        "category",
        '"priority":',
        "scoring_context",
        "as_of",
    ):
        assert sentinel not in serialized


@pytest.mark.parametrize("action", list(SuggestedAction))
def test_production_serializer_exposes_all_action_values_and_labels(action):
    base = build_opportunity_score(opportunity_id=_card()["id"])
    score = replace(
        base,
        suggested_action=SuggestedActionResult(
            action=action,
            reason_code="characterized_action",
            explanation="Internal action prose is not public.",
        ),
    )

    summary = serialize_command_center_intelligence(score)

    assert summary["action"] == action.value
    assert summary["action_label"] == ACTION_LABELS[action]
    assert "Internal action prose" not in json.dumps(summary)


@pytest.mark.parametrize("level", ["High", "Medium", "Low", "Not Scored"])
def test_production_serializer_uses_generic_confidence_summaries(level):
    base = build_opportunity_score(opportunity_id=_card()["id"])
    score = replace(
        base,
        confidence=ScoreConfidence(level=level, summary="PRIVATE TRUST SENTINEL"),
    )

    summary = serialize_command_center_intelligence(score)

    assert summary["confidence"]["level"] == level
    assert "PRIVATE TRUST SENTINEL" not in json.dumps(summary)
