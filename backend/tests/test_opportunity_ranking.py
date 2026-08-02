from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import json
from uuid import UUID

import pytest

from app.services.opportunity_score import (
    ScoreCategory,
    ScoreFactor,
    build_opportunity_ranking_entry,
    build_opportunity_score,
    rank_opportunity_entries,
)
from tests.intelligence_builders import fixed_as_of, opportunity, opportunity_snapshot


IDS = tuple(UUID(f"00000000-0000-0000-0000-{index:012d}") for index in range(1, 10))


def completed_score(opportunity_id: UUID, total: int = 50, *, hard_override=False):
    if hard_override:
        return build_opportunity_score(
            opportunity_id=str(opportunity_id),
            hard_override_reason="discarded",
        )
    remaining = total - 50
    factors = []
    for index, (category, minimum, maximum) in enumerate(
        (
            (ScoreCategory.MATCH_QUALITY, -35, 30),
            (ScoreCategory.CAREER_VALUE, -10, 20),
            (ScoreCategory.PRACTICALITY, -25, 20),
            (ScoreCategory.CONFIDENCE, -20, 15),
            (ScoreCategory.ACTOR_INTEREST, -20, 15),
        )
    ):
        points = min(maximum, max(minimum, remaining))
        remaining -= points
        if points:
            factors.append(
                ScoreFactor(
                    f"{category.value}.ranking.{index}",
                    category,
                    points,
                    "Controlled ranking score contribution.",
                    index,
                )
            )
    assert remaining == 0
    result = build_opportunity_score(opportunity_id=str(opportunity_id), factors=factors)
    assert result.overall_score == total
    return result


def projection(
    index: int,
    *,
    total: int = 50,
    project: str | None = "Project",
    role: str | None = "Role",
    url: str | None = "https://example.test/casting",
    submission_deadline=None,
    audition_deadline=None,
    is_duplicate: bool = False,
):
    identifier = IDS[index]
    item = opportunity(
        id=identifier,
        project=project,
        role=role,
        original_post_url=url,
        submission_deadline=submission_deadline,
        audition_deadline=audition_deadline,
        is_duplicate=is_duplicate,
    )
    return build_opportunity_ranking_entry(
        item,
        completed_score(identifier, total),
        as_of=fixed_as_of(),
    )


def ranked_ids(entries):
    return tuple(entry.opportunity_id for entry in rank_opportunity_entries(entries))


def test_projection_contains_only_the_approved_immutable_fields():
    deadline = fixed_as_of() + timedelta(days=2)
    entry = projection(0, total=70, submission_deadline=deadline)
    assert entry.opportunity_id == IDS[0]
    assert entry.score.overall_score == 70
    assert entry.actionable_deadline == deadline.astimezone(timezone.utc)
    assert entry.project_key == "project"
    assert entry.role_key == "role"
    assert entry.source_url_key == "https://example.test/casting"
    assert set(entry.as_dict()) == {
        "opportunity_id",
        "score",
        "actionable_deadline",
        "project_key",
        "role_key",
        "source_url_key",
    }
    with pytest.raises(FrozenInstanceError):
        entry.project_key = "changed"


def test_score_ordering_includes_zero_hard_override_and_ties_continue_to_deadline():
    later = fixed_as_of() + timedelta(days=4)
    earlier = fixed_as_of() + timedelta(days=1)
    high = projection(0, total=80, submission_deadline=later)
    tied_later = projection(1, total=60, submission_deadline=later)
    tied_earlier = projection(2, total=60, submission_deadline=earlier)
    hard_id = IDS[3]
    hard_item = opportunity(id=hard_id)
    hard = build_opportunity_ranking_entry(
        hard_item,
        completed_score(hard_id, hard_override=True),
        as_of=fixed_as_of(),
    )
    assert ranked_ids((hard, tied_later, high, tied_earlier)) == (
        IDS[0],
        IDS[2],
        IDS[1],
        IDS[3],
    )


def test_deadline_projection_selects_earliest_future_and_puts_missing_last():
    past = fixed_as_of() - timedelta(seconds=1)
    earlier = fixed_as_of() + timedelta(hours=2)
    later = fixed_as_of() + timedelta(hours=5)
    submission_wins = projection(0, submission_deadline=earlier, audition_deadline=later)
    audition_wins = projection(1, submission_deadline=later, audition_deadline=earlier)
    expired_plus_valid = projection(2, submission_deadline=past, audition_deadline=later)
    all_expired = projection(3, submission_deadline=past, audition_deadline=past)
    missing = projection(4)
    assert submission_wins.actionable_deadline == earlier
    assert audition_wins.actionable_deadline == earlier
    assert expired_plus_valid.actionable_deadline == later
    assert all_expired.actionable_deadline is None
    assert ranked_ids((missing, expired_plus_valid, all_expired, audition_wins)) == (
        IDS[1],
        IDS[2],
        IDS[3],
        IDS[4],
    )


def test_deadline_normalizes_naive_and_equivalent_timezone_instants_to_utc():
    naive = datetime(2026, 8, 3, 16, 0)
    utc = datetime(2026, 8, 3, 16, 0, tzinfo=timezone.utc)
    eastern = utc.astimezone(timezone(timedelta(hours=-4)))
    naive_entry = projection(0, submission_deadline=naive)
    utc_entry = projection(1, submission_deadline=utc)
    eastern_entry = projection(2, submission_deadline=eastern)
    assert naive_entry.actionable_deadline == utc
    assert utc_entry.actionable_deadline == eastern_entry.actionable_deadline == utc


def test_projection_rejects_naive_as_of():
    item = opportunity(id=IDS[0])
    with pytest.raises(ValueError, match="as_of must be timezone-aware"):
        build_opportunity_ranking_entry(
            item,
            completed_score(IDS[0]),
            as_of=datetime(2026, 8, 2, 12, 0),
        )


@pytest.mark.parametrize(
    ("field", "values", "expected_indices"),
    [
        ("project", ("Zulu", "  alpha   show ", "ALPHA Show"), (1, 2, 0)),
        ("role", ("Zulu", "  alpha   role ", "ALPHA Role"), (1, 2, 0)),
        ("project", ("Straße", "STRASSE", "zeta"), (0, 1, 2)),
        ("role", ("Straße", "STRASSE", "zeta"), (0, 1, 2)),
        ("project", ("Zulu", "", None), (1, 2, 0)),
        ("role", ("Zulu", "", None), (1, 2, 0)),
    ],
)
def test_project_and_role_normalization_and_order(field, values, expected_indices):
    entries = []
    for index, value in enumerate(values):
        kwargs = {field: value}
        entries.append(projection(index, **kwargs))
    assert ranked_ids(reversed(entries)) == tuple(IDS[index] for index in expected_indices)


def test_canonical_url_normalization_prevents_raw_string_order_divergence():
    first = projection(
        0,
        url="HTTPS://Example.Test:443/path?utm_source=mail&b=2&a=1#section",
    )
    equivalent = projection(1, url="https://example.test/path?a=1&b=2")
    later = projection(2, url="https://example.test/z")
    assert first.source_url_key == equivalent.source_url_key
    assert ranked_ids((later, equivalent, first)) == (IDS[0], IDS[1], IDS[2])


def test_blank_and_missing_urls_sort_before_present_url():
    present = projection(0, url="https://example.test/z")
    blank = projection(1, url="  ")
    missing = projection(2, url=None)
    assert blank.source_url_key == missing.source_url_key == ""
    assert ranked_ids((present, missing, blank)) == (IDS[1], IDS[2], IDS[0])


def test_invalid_or_credential_bearing_source_url_is_rejected_by_existing_policy():
    for raw in ("not-a-url", "https://user:secret@example.test/private"):
        with pytest.raises(ValueError):
            projection(0, url=raw)


def test_complete_tie_uses_uuid_text_and_is_independent_of_input_order():
    entries = tuple(projection(index) for index in (4, 2, 0, 3, 1))
    expected = tuple(sorted((IDS[index] for index in (4, 2, 0, 3, 1)), key=str))
    assert ranked_ids(entries) == expected
    assert ranked_ids(reversed(entries)) == expected


def test_each_tie_break_field_precedes_the_fields_after_it():
    deadline = fixed_as_of() + timedelta(days=1)
    high_score_late_text = projection(0, total=51, project="Zulu")
    low_score_early_text = projection(1, total=50, project="Alpha")
    assert ranked_ids((low_score_early_text, high_score_late_text)) == (IDS[0], IDS[1])

    earlier_zulu = projection(2, project="Zulu", submission_deadline=deadline)
    missing_alpha = projection(3, project="Alpha")
    assert ranked_ids((missing_alpha, earlier_zulu)) == (IDS[2], IDS[3])

    project_alpha_role_zulu = projection(4, project="Alpha", role="Zulu")
    project_zulu_role_alpha = projection(5, project="Zulu", role="Alpha")
    assert ranked_ids((project_zulu_role_alpha, project_alpha_role_zulu)) == (
        IDS[4],
        IDS[5],
    )

    role_alpha_url_zulu = projection(6, project="Same", role="Alpha", url="https://example.test/z")
    role_zulu_url_alpha = projection(7, project="Same", role="Zulu", url="https://example.test/a")
    assert ranked_ids((role_zulu_url_alpha, role_alpha_url_zulu)) == (IDS[6], IDS[7])


def test_duplicate_input_uuid_is_rejected_without_merging():
    entry = projection(0)
    with pytest.raises(
        ValueError,
        match=f"duplicate opportunity IDs are not allowed: {IDS[0]}",
    ):
        rank_opportunity_entries((entry, entry))


def test_same_title_url_and_product_duplicate_flag_with_distinct_ids_are_allowed():
    first = projection(0, is_duplicate=True)
    second = projection(1, is_duplicate=True)
    assert ranked_ids((second, first)) == (IDS[0], IDS[1])


def test_score_identity_and_version_are_validated():
    item = opportunity(id=IDS[0])
    with pytest.raises(ValueError, match="does not match"):
        build_opportunity_ranking_entry(
            item,
            completed_score(IDS[1]),
            as_of=fixed_as_of(),
        )
    unsupported = replace(completed_score(IDS[0]), scoring_version=2)
    with pytest.raises(ValueError, match="only scoring version 1"):
        build_opportunity_ranking_entry(item, unsupported, as_of=fixed_as_of())


def test_empty_and_singleton_inputs_return_immutable_tuples():
    assert rank_opportunity_entries(()) == ()
    entry = projection(0)
    assert rank_opportunity_entries((entry,)) == (entry,)


def test_projection_and_ranking_are_read_only_and_serially_deterministic():
    item = opportunity(
        id=IDS[0],
        submission_deadline=fixed_as_of() + timedelta(days=1),
    )
    score = completed_score(IDS[0], 70)
    item_before = opportunity_snapshot(item)
    score_before = deepcopy(score)
    first = build_opportunity_ranking_entry(item, score, as_of=fixed_as_of())
    second = build_opportunity_ranking_entry(item, score, as_of=fixed_as_of())
    first_output = json.dumps(
        [entry.as_dict() for entry in rank_opportunity_entries((first,))],
        sort_keys=True,
        separators=(",", ":"),
    )
    second_output = json.dumps(
        [entry.as_dict() for entry in rank_opportunity_entries((second,))],
        sort_keys=True,
        separators=(",", ":"),
    )
    assert first_output == second_output
    assert opportunity_snapshot(item) == item_before
    assert score == score_before
    assert score.suggested_action == score_before.suggested_action


def test_ranker_accepts_only_frozen_projections_and_cannot_inspect_orm_state():
    with pytest.raises(ValueError, match="only OpportunityRankingEntry"):
        rank_opportunity_entries((object(),))
