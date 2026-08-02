from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from app.db.models import Submission
from app.services.command_center_service import CommandCenterService
from app.services.opportunity_score import (
    FeedbackScoringEntry,
    OpportunityScoringContext,
    build_opportunity_score,
    rank_opportunity_entries,
)
from tests.intelligence_builders import actor_profile, fixed_as_of, opportunity


def _candidate(index: int, **overrides):
    values = {
        "id": UUID(f"20000000-0000-0000-0000-{index + 1:012d}"),
        "project": f"Project {index}",
        "role": f"Role {index}",
    }
    values.update(overrides)
    return opportunity(**values)


def test_consumer_scores_one_full_batch_with_one_shared_as_of_and_one_rank_call():
    candidates = [
        _candidate(0, project="Zulu"),
        _candidate(1, project="Alpha"),
        _candidate(2, project="Middle"),
    ]
    contexts = {candidate.id: OpportunityScoringContext() for candidate in candidates}
    service = CommandCenterService(MagicMock())
    service._read_scoring_contexts = MagicMock(return_value=contexts)

    def controlled_score(item, _actor, context, *, as_of):
        assert as_of is fixed_as_of_value
        assert context is contexts[item.id]
        return build_opportunity_score(opportunity_id=str(item.id))

    fixed_as_of_value = fixed_as_of()
    with (
        patch(
            "app.services.command_center_service.OpportunityIntelligenceService"
        ) as intelligence_type,
        patch(
            "app.services.command_center_service.rank_opportunity_entries",
            wraps=rank_opportunity_entries,
        ) as rank_batch,
    ):
        intelligence_type.return_value.score.side_effect = controlled_score
        result = service._ranked_opportunities(candidates, actor_profile(), as_of=fixed_as_of_value)

    assert [item.project for item in result] == ["Alpha", "Middle", "Zulu"]
    assert intelligence_type.return_value.score.call_count == len(candidates)
    rank_batch.assert_called_once()


def test_consumer_preserves_ranker_duplicate_identity_validation():
    candidate = _candidate(0)
    service = CommandCenterService(MagicMock())
    service._read_scoring_contexts = MagicMock(
        return_value={candidate.id: OpportunityScoringContext()}
    )

    with patch(
        "app.services.command_center_service.OpportunityIntelligenceService"
    ) as intelligence_type:
        intelligence_type.return_value.score.return_value = build_opportunity_score(
            opportunity_id=str(candidate.id)
        )
        with pytest.raises(ValueError, match="duplicate opportunity IDs"):
            service._ranked_opportunities(
                [candidate, candidate], actor_profile(), as_of=fixed_as_of()
            )


def test_consumer_preserves_complete_ranking_tie_break_chain():
    deadline = fixed_as_of() + timedelta(days=1)
    candidates = [
        _candidate(0, project="Zulu", role="Zulu"),
        _candidate(1, project="Zulu", role="Zulu", submission_deadline=deadline),
        _candidate(2, project="Alpha", role="Zulu"),
        _candidate(3, project="Role", role="Alpha"),
        _candidate(4, project="Role", role="Zulu"),
        _candidate(5, project="Tie", role="Same", original_post_url="https://example.test/a"),
        _candidate(6, project="Tie", role="Same", original_post_url="https://example.test/z"),
        _candidate(7, project="Tie", role="Same", original_post_url="https://example.test/z"),
    ]
    contexts = {candidate.id: OpportunityScoringContext() for candidate in candidates}
    service = CommandCenterService(MagicMock())
    service._read_scoring_contexts = MagicMock(return_value=contexts)

    def controlled_score(item, _actor, _context, *, as_of):
        assert as_of == fixed_as_of()
        score = build_opportunity_score(opportunity_id=str(item.id))
        return replace(score, overall_score=51) if item is candidates[0] else score

    with patch(
        "app.services.command_center_service.OpportunityIntelligenceService"
    ) as intelligence_type:
        intelligence_type.return_value.score.side_effect = controlled_score
        result = service._ranked_opportunities(candidates, actor_profile(), as_of=fixed_as_of())

    assert [item.id for item in result] == [
        candidates[0].id,
        candidates[1].id,
        candidates[2].id,
        candidates[3].id,
        candidates[4].id,
        candidates[5].id,
        candidates[6].id,
        candidates[7].id,
    ]


def test_equivalent_as_of_instants_produce_the_same_order():
    first = _candidate(
        0,
        submission_deadline=fixed_as_of() + timedelta(days=1),
    )
    second = _candidate(1, submission_deadline=None)
    candidates = [second, first]
    contexts = {candidate.id: OpportunityScoringContext() for candidate in candidates}
    service = CommandCenterService(MagicMock())
    service._read_scoring_contexts = MagicMock(return_value=contexts)

    utc_result = service._ranked_opportunities(candidates, actor_profile(), as_of=fixed_as_of())
    eastern_result = service._ranked_opportunities(
        candidates,
        actor_profile(),
        as_of=fixed_as_of().astimezone(timezone(timedelta(hours=-4))),
    )

    assert [item.id for item in utc_result] == [item.id for item in eastern_result]


def test_context_uses_only_persisted_bounded_values_and_no_orm_references():
    same_time = datetime(2027, 1, 1, 12, 0, tzinfo=timezone.utc)
    lower_id = Submission(
        id=UUID("40000000-0000-0000-0000-000000000001"),
        actor_profile_id=actor_profile().id,
        opportunity_id=_candidate(0).id,
        current_status="Requested",
        submitted_at=same_time,
        created_at=same_time,
        updated_at=same_time,
        notes="PRIVATE SUBMISSION NOTE",
    )
    higher_id = Submission(
        id=UUID("40000000-0000-0000-0000-000000000002"),
        actor_profile_id=actor_profile().id,
        opportunity_id=_candidate(0).id,
        current_status="Booked",
        submitted_at=same_time,
        created_at=same_time,
        updated_at=same_time,
        notes="ANOTHER PRIVATE NOTE",
    )
    item = _candidate(
        0,
        submissions=[higher_id, lower_id],
        watchlist_match_names=[
            {
                "id": "watch-1",
                "title": "Casting Office",
                "priority": "High",
                "matched_terms": ["private raw term"],
            },
            {"id": "ignored", "priority": "Unsupported"},
            "not-a-structured-match",
        ],
    )
    feedback = FeedbackScoringEntry(
        key="feedback-1",
        feedback_type="This Fits Me",
        created_at=same_time,
    )

    context = CommandCenterService._build_scoring_context(
        item,
        feedback=feedback,
        audition_travel_limit_hours=2.0,
    )

    assert context == OpportunityScoringContext(
        watchlist_matches=context.watchlist_matches,
        submission_status="Requested",
        feedback_entries=(feedback,),
        audition_travel_limit_hours=2.0,
    )
    assert context.watchlist_matches[0].key == "watch-1"
    assert context.career_goal_matches == ()
    assert context.dream_target_matches == ()
    assert context.stretch_archetype_matches == ()
    assert "PRIVATE" not in repr(context)
    assert not any(
        hasattr(value, "__mapper__")
        for value in (
            *context.watchlist_matches,
            *context.feedback_entries,
        )
    )


def test_missing_optional_context_is_neutral():
    item = _candidate(0, submissions=[], watchlist_match_names=[])

    assert CommandCenterService._build_scoring_context(item) == OpportunityScoringContext()


def test_missing_actor_preserves_bounded_legacy_order_without_fabricating_profile():
    candidates = [
        _candidate(0, urgency_score=5, quality_score=90),
        _candidate(1, urgency_score=90, quality_score=5),
    ]
    service = CommandCenterService(MagicMock())
    service._read_scoring_contexts = MagicMock()

    result = service._ranked_opportunities(candidates, None, as_of=fixed_as_of())

    assert [item.id for item in result] == [candidates[1].id, candidates[0].id]
    service._read_scoring_contexts.assert_not_called()
