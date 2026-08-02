from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json

import pytest

from app.services.opportunity_intelligence_service import OpportunityIntelligenceService
from app.services.opportunity_score import (
    FeedbackScoringEntry,
    OpportunityScoringContext,
    ScoreCategory,
    ScoreFactor,
    WatchListScoringMatch,
    build_opportunity_score,
)
from tests.intelligence_builders import (
    actor_profile,
    fixed_as_of,
    opportunity,
    opportunity_snapshot,
)


def score(item=None, context=None, *, as_of=None):
    return OpportunityIntelligenceService(None).score(
        item or opportunity(),
        actor_profile(),
        context or OpportunityScoringContext(),
        as_of=as_of or fixed_as_of(),
    )


def factors(result, category):
    return next(item for item in result.categories if item.category is category).factors


def factor(result, category, prefix):
    return next(item for item in factors(result, category) if item.id.startswith(prefix))


@pytest.mark.parametrize(
    ("remaining", "factor_id", "points"),
    [
        (timedelta(hours=24) - timedelta(seconds=1), "practicality.deadline.within_24h", 8),
        (timedelta(hours=24), "practicality.deadline.within_24h", 8),
        (timedelta(hours=24) + timedelta(seconds=1), "practicality.deadline.within_72h", 5),
        (timedelta(hours=72), "practicality.deadline.within_72h", 5),
        (timedelta(hours=72) + timedelta(seconds=1), "practicality.deadline.within_7d", 2),
        (timedelta(hours=168), "practicality.deadline.within_7d", 2),
        (timedelta(hours=168) + timedelta(seconds=1), "practicality.deadline.distant", 0),
    ],
)
def test_deadline_boundaries(remaining, factor_id, points):
    result = score(opportunity(submission_deadline=fixed_as_of() + remaining))
    deadline = factor(result, ScoreCategory.PRACTICALITY, "practicality.deadline.")
    assert (deadline.id, deadline.points, deadline.priority) == (factor_id, points, 240)


def test_deadline_uses_earliest_future_and_equivalent_timezone_instant():
    earliest = fixed_as_of() + timedelta(hours=48)
    item = opportunity(
        submission_deadline=fixed_as_of() - timedelta(hours=1),
        audition_deadline=earliest.astimezone(timezone(timedelta(hours=-4))),
    )
    deadline = factor(score(item), ScoreCategory.PRACTICALITY, "practicality.deadline.")
    assert deadline.id == "practicality.deadline.within_72h"


def test_missing_and_unusable_deadlines_get_one_missing_factor():
    item = opportunity(submission_deadline=None, audition_deadline=None)
    item.submission_deadline = "not-a-date"
    deadline = factor(score(item), ScoreCategory.PRACTICALITY, "practicality.deadline.")
    assert (deadline.id, deadline.points) == ("practicality.deadline.missing", -5)


@pytest.mark.parametrize("modality", ["Self-Tape", "SELF-TAPE", "Virtual", "virtual"])
def test_documented_remote_modalities_score_once(modality):
    remote = factor(
        score(opportunity(audition_type=modality)),
        ScoreCategory.PRACTICALITY,
        "practicality.audition.",
    )
    assert (remote.id, remote.points, remote.priority) == (
        "practicality.audition.remote",
        8,
        200,
    )


def test_local_travel_exception_coverage_and_compensation_rules():
    context = OpportunityScoringContext(audition_travel_limit_hours=2)
    local = score(opportunity(audition_type="In-Person", audition_drive_time=1.5), context)
    assert factor(local, ScoreCategory.PRACTICALITY, "practicality.travel.local").points == 4

    exception = score(
        opportunity(
            audition_type="In-Person",
            audition_drive_time=1,
            visibility_status="travel_exception",
            travel_covered=True,
            housing_covered=True,
            rate="$500/day",
        ),
        context,
    )
    values = {item.id: item.points for item in factors(exception, ScoreCategory.PRACTICALITY)}
    assert "practicality.travel.local" not in values
    assert values["practicality.travel.exception"] == -15
    assert values["practicality.travel.covered"] == 4
    assert values["practicality.housing.covered"] == 4
    assert values["practicality.compensation.known"] == 3


@pytest.mark.parametrize("rate", [None, "", "   ", "Unknown", "TBD"])
def test_missing_compensation_is_neutral(rate):
    ids = {item.id for item in factors(score(opportunity(rate=rate)), ScoreCategory.PRACTICALITY)}
    assert "practicality.compensation.known" not in ids


@pytest.mark.parametrize(
    ("value", "factor_id", "points"),
    [
        (85, "confidence.parser.high", 6),
        (84.999, "confidence.parser.medium", 3),
        (70, "confidence.parser.medium", 3),
        (69.999, "confidence.parser.low", -6),
        (0, "confidence.parser.low", -6),
        ("85", "confidence.parser.high", 6),
        (None, "confidence.parser.missing", -4),
        ("bad", "confidence.parser.missing", -4),
        (101, "confidence.parser.missing", -4),
        (-1, "confidence.parser.missing", -4),
    ],
)
def test_parse_confidence_contract(value, factor_id, points):
    result = score(opportunity(source_metadata={"breakdown_parse_confidence": value}))
    parsed = factor(result, ScoreCategory.CONFIDENCE, "confidence.parser.")
    assert (parsed.id, parsed.points, parsed.priority) == (factor_id, points, 300)


@pytest.mark.parametrize(
    ("status", "factor_id", "points"),
    [
        ("Verified", "confidence.trust.verified", 5),
        ("Pass", "confidence.trust.verified", 5),
        ("Review", "confidence.trust.review", -5),
        ("Warning", "confidence.trust.review", -5),
        ("Needs Info", "confidence.trust.review", -5),
        ("Blocked", "confidence.trust.review", -5),
    ],
)
def test_trust_contract(status, factor_id, points):
    result = score(opportunity(source_metadata={"trust_verification": {"status": status}}))
    trust = factor(result, ScoreCategory.CONFIDENCE, "confidence.trust.")
    assert (trust.id, trust.points, trust.priority) == (factor_id, points, 310)


@pytest.mark.parametrize("status", [None, "Unsupported"])
def test_unknown_trust_is_neutral(status):
    metadata = {} if status is None else {"trust_verification": {"status": status}}
    ids = {
        item.id
        for item in factors(score(opportunity(source_metadata=metadata)), ScoreCategory.CONFIDENCE)
    }
    assert not any(value.startswith("confidence.trust.") for value in ids)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.85, 4),
        (0.849, 2),
        (0.70, 2),
        (0.699, None),
        (0.50, None),
        (0.499, -4),
        (None, None),
        ("bad", None),
        (1.1, None),
    ],
)
def test_source_reliability_boundaries(value, expected):
    values = [
        item.points
        for item in factors(
            score(opportunity(source_reliability_score=value)), ScoreCategory.CONFIDENCE
        )
        if item.id.startswith("confidence.source.")
    ]
    assert values == ([] if expected is None else [expected])


def test_completeness_uses_only_the_seven_versioned_critical_fields():
    complete = factor(score(opportunity()), ScoreCategory.CONFIDENCE, "confidence.completeness.")
    assert (complete.id, complete.points) == ("confidence.completeness.complete", 4)

    one_missing = factors(score(opportunity(location="")), ScoreCategory.CONFIDENCE)
    assert not any(item.id.startswith("confidence.completeness.") for item in one_missing)

    two_missing = factor(
        score(opportunity(location="Unknown", description="TBD")),
        ScoreCategory.CONFIDENCE,
        "confidence.completeness.",
    )
    assert (two_missing.id, two_missing.points) == ("confidence.completeness.incomplete", -5)


@pytest.mark.parametrize("priority,points", [("High", 8), ("Medium", 5), ("Low", 3)])
def test_watchlist_priority_points(priority, points):
    context = OpportunityScoringContext(
        watchlist_matches=(WatchListScoringMatch("Detective", priority),)
    )
    selected = factor(score(context=context), ScoreCategory.ACTOR_INTEREST, "interest.watchlist.")
    assert (selected.id, selected.points, selected.priority) == (
        f"interest.watchlist.{priority.lower()}",
        points,
        400,
    )


def test_watchlist_selection_is_highest_enabled_and_order_independent():
    matches = (
        WatchListScoringMatch("private-note-not-used", "Low"),
        WatchListScoringMatch("Detective", "High"),
        WatchListScoringMatch("Disabled", "High", enabled=False),
        WatchListScoringMatch("Detective", "High"),
    )
    forward = score(context=OpportunityScoringContext(watchlist_matches=matches)).as_dict()
    reverse = score(
        context=OpportunityScoringContext(watchlist_matches=tuple(reversed(matches)))
    ).as_dict()
    assert forward == reverse
    assert "private-note-not-used" not in json.dumps(forward)


@pytest.mark.parametrize(
    ("feedback_type", "factor_id", "points"),
    [
        ("This Fits Me", "interest.feedback.fits_me", 6),
        ("Interesting Stretch", "interest.feedback.interesting_stretch", 4),
        ("Save For Later", "interest.feedback.save_later", 2),
        ("Not My Type", "interest.feedback.not_my_type", -8),
    ],
)
def test_feedback_points(feedback_type, factor_id, points):
    context = OpportunityScoringContext(
        feedback_entries=(FeedbackScoringEntry("feedback-1", feedback_type, fixed_as_of()),)
    )
    selected = factor(score(context=context), ScoreCategory.ACTOR_INTEREST, "interest.feedback.")
    assert (selected.id, selected.points, selected.priority) == (factor_id, points, 410)


def test_latest_feedback_and_equal_timestamp_key_tie_break_are_deterministic():
    entries = (
        FeedbackScoringEntry("z-key", "Not My Type", fixed_as_of()),
        FeedbackScoringEntry("a-key", "This Fits Me", fixed_as_of()),
        FeedbackScoringEntry("old", "Save For Later", fixed_as_of() - timedelta(days=1)),
    )
    forward = score(context=OpportunityScoringContext(feedback_entries=entries)).as_dict()
    reverse = score(
        context=OpportunityScoringContext(feedback_entries=tuple(reversed(entries)))
    ).as_dict()
    assert forward == reverse
    selected = next(
        item
        for category in forward["categories"]
        for item in category["factors"]
        if item["id"].startswith("interest.feedback.")
    )
    assert selected["id"] == "interest.feedback.fits_me"


def test_context_rejects_naive_feedback_timestamp():
    with pytest.raises(ValueError, match="timezone-aware"):
        FeedbackScoringEntry("feedback", "This Fits Me", datetime(2026, 8, 2))


def test_unsupported_feedback_is_typed_but_point_neutral():
    context = OpportunityScoringContext(
        feedback_entries=(FeedbackScoringEntry("feedback", "Unsupported", fixed_as_of()),)
    )
    assert not factors(score(context=context), ScoreCategory.ACTOR_INTEREST)


@pytest.mark.parametrize(
    "submission_status",
    ["Submitted", "Requested", "Pinned", "Passed", "Booked", "No Response"],
)
def test_submission_status_is_typed_but_point_neutral(submission_status):
    baseline = score().overall_score
    result = score(context=OpportunityScoringContext(submission_status=submission_status))
    assert result.overall_score == baseline
    assert not any(
        item.id.startswith("interest.submission")
        for item in factors(result, ScoreCategory.ACTOR_INTEREST)
    )


def test_new_category_caps_apply_before_final_normalization():
    factors_to_cap = (
        [
            ScoreFactor(
                f"practicality.test.{index}", ScoreCategory.PRACTICALITY, 10, "Cap test.", index
            )
            for index in range(3)
        ]
        + [
            ScoreFactor(
                f"confidence.test.{index}", ScoreCategory.CONFIDENCE, -10, "Cap test.", index
            )
            for index in range(3)
        ]
        + [
            ScoreFactor(
                f"interest.test.{index}", ScoreCategory.ACTOR_INTEREST, 10, "Cap test.", index
            )
            for index in range(2)
        ]
    )
    result = build_opportunity_score(opportunity_id="test", factors=factors_to_cap)
    by_category = {item.category: item for item in result.categories}
    assert (
        by_category[ScoreCategory.PRACTICALITY].raw_subtotal,
        by_category[ScoreCategory.PRACTICALITY].capped_subtotal,
    ) == (30, 20)
    assert (
        by_category[ScoreCategory.CONFIDENCE].raw_subtotal,
        by_category[ScoreCategory.CONFIDENCE].capped_subtotal,
    ) == (-30, -20)
    assert (
        by_category[ScoreCategory.ACTOR_INTEREST].raw_subtotal,
        by_category[ScoreCategory.ACTOR_INTEREST].capped_subtotal,
    ) == (20, 15)
    assert result.overall_score == 65


@pytest.mark.parametrize(
    ("category", "points", "count", "expected"),
    [
        (ScoreCategory.PRACTICALITY, 10, 3, 20),
        (ScoreCategory.PRACTICALITY, -10, 3, -25),
        (ScoreCategory.CONFIDENCE, 10, 2, 15),
        (ScoreCategory.CONFIDENCE, -10, 3, -20),
        (ScoreCategory.ACTOR_INTEREST, 10, 2, 15),
        (ScoreCategory.ACTOR_INTEREST, -10, 3, -20),
    ],
)
def test_each_new_category_enforces_both_caps(category, points, count, expected):
    result = build_opportunity_score(
        opportunity_id="test",
        factors=[
            ScoreFactor(f"{category.value}.cap.{index}", category, points, "Cap test.", index)
            for index in range(count)
        ],
    )
    category_score = next(item for item in result.categories if item.category is category)
    assert category_score.raw_subtotal == points * count
    assert category_score.capped_subtotal == expected


@pytest.mark.parametrize(("points", "level"), [(10, "High"), (0, "Medium"), (-1, "Low")])
def test_confidence_summary_is_deterministic(points, level):
    result = build_opportunity_score(
        opportunity_id="test",
        factors=[
            ScoreFactor(
                "confidence.summary.test",
                ScoreCategory.CONFIDENCE,
                points,
                "Confidence summary test.",
                300,
            )
        ],
    )
    assert result.confidence.level == level
    assert result.confidence.summary == (
        f"{level} confidence: 1 bounded confidence factors contribute {points:+d} points."
    )


def test_positive_new_factors_cannot_overcome_hard_override():
    item = opportunity(hidden_by_rule="user_rejected")
    context = OpportunityScoringContext(
        watchlist_matches=(WatchListScoringMatch("Detective", "High"),),
        feedback_entries=(FeedbackScoringEntry("feedback", "This Fits Me", fixed_as_of()),),
    )
    result = score(item, context)
    assert result.hard_override_reason == "user_rejected"
    assert result.overall_score == 0
    assert all(not category.factors for category in result.categories)


def test_scoring_is_read_only_and_repeatable():
    item = opportunity(submission_deadline=fixed_as_of() + timedelta(hours=24))
    actor = actor_profile()
    context = OpportunityScoringContext(
        watchlist_matches=(WatchListScoringMatch("Detective", "High"),),
        feedback_entries=(FeedbackScoringEntry("feedback", "This Fits Me", fixed_as_of()),),
    )
    item_before = opportunity_snapshot(item)
    actor_before = {
        attribute.key: deepcopy(getattr(actor, attribute.key))
        for attribute in actor.__mapper__.column_attrs
    }
    context_before = deepcopy(context)
    first = OpportunityIntelligenceService(None).score(item, actor, context, as_of=fixed_as_of())
    second = OpportunityIntelligenceService(None).score(item, actor, context, as_of=fixed_as_of())
    assert first.as_dict() == second.as_dict()
    assert opportunity_snapshot(item) == item_before
    assert {
        attribute.key: deepcopy(getattr(actor, attribute.key))
        for attribute in actor.__mapper__.column_attrs
    } == actor_before
    assert context == context_before


def test_naive_as_of_remains_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        score(as_of=datetime(2026, 8, 2, 12, 0))
