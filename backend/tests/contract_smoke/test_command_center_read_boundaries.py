from __future__ import annotations

from datetime import datetime, timedelta, timezone
from copy import deepcopy
from uuid import UUID

import pytest
from sqlalchemy import event, func, inspect, select
from sqlalchemy.orm.attributes import NO_VALUE


pytestmark = pytest.mark.contract_smoke

AS_OF = datetime(2027, 1, 15, 15, 0, tzinfo=timezone.utc)


def _opportunity(index: int, **overrides):
    from app.db.models import Opportunity

    values = {
        "id": UUID(int=index + 1),
        "role": f"Role {index:03d}",
        "project": f"Project {index:03d}",
        "union": "SAG-AFTRA",
        "location": "New York, NY",
        "description": "A deterministic command-center candidate.",
        "breakdown_classification": "Acting Role",
        "visibility_status": "visible",
        "is_demo_data": False,
        "created_at": AS_OF - timedelta(minutes=index),
        "updated_at": AS_OF,
    }
    values.update(overrides)
    return Opportunity(**values)


def _actor():
    from app.db.models import ActorProfile

    return ActorProfile(
        id=UUID("10000000-0000-0000-0000-000000000001"),
        name="Command Center Test Actor",
        sag_status="SAG-AFTRA",
        union_status="SAG-AFTRA",
        current_location="New York, NY",
        playable_age_min=30,
        playable_age_max=40,
        skills=[],
        gender_identities=[],
        ethnicities=[],
        racial_identities=[],
        nationalities=[],
        languages=["English"],
        accents=[],
        disability_identities=[],
        included_role_types=["Guest Star"],
        excluded_role_types=[],
    )


def _table_counts(db):
    from app.db.models import (
        ActorProfile,
        Asset,
        CareerDevelopmentTask,
        CastingGoal,
        ChiefOfStaffState,
        DreamRoleTarget,
        MaterialGapAlert,
        Opportunity,
        OutcomeNudge,
        RecommendationFeedback,
        Submission,
        TravelPreference,
        WatchList,
    )

    models = (
        Opportunity,
        ActorProfile,
        ChiefOfStaffState,
        MaterialGapAlert,
        OutcomeNudge,
        Submission,
        Asset,
        CareerDevelopmentTask,
        CastingGoal,
        DreamRoleTarget,
        WatchList,
        RecommendationFeedback,
        TravelPreference,
    )
    return {
        model.__tablename__: db.scalar(select(func.count()).select_from(model)) for model in models
    }


def test_read_snapshot_is_idempotent_and_does_not_write(db, monkeypatch):
    from app.services.command_center_service import CommandCenterService

    service = CommandCenterService(db)
    before = _table_counts(db)
    writes: list[str] = []
    monkeypatch.setattr(db, "add", lambda *_args, **_kwargs: writes.append("add"))
    monkeypatch.setattr(db, "flush", lambda *_args, **_kwargs: writes.append("flush"))
    monkeypatch.setattr(db, "commit", lambda *_args, **_kwargs: writes.append("commit"))
    monkeypatch.setattr(db, "rollback", lambda *_args, **_kwargs: writes.append("rollback"))

    select_count = 0

    def count_selects(_conn, _cursor, statement, _parameters, _context, _many):
        nonlocal select_count
        if statement.lstrip().upper().startswith("SELECT"):
            select_count += 1

    bind = db.get_bind()
    event.listen(bind, "before_cursor_execute", count_selects)
    try:
        first = service.read_snapshot(
            actor=None,
            as_of=AS_OF,
            since_at=AS_OF - timedelta(days=7),
        )
        first_read_count = select_count
        second = service.read_snapshot(
            actor=None,
            as_of=AS_OF,
            since_at=AS_OF - timedelta(days=7),
        )
        second_read_count = select_count - first_read_count
    finally:
        event.remove(bind, "before_cursor_execute", count_selects)

    assert first == second
    assert first_read_count == second_read_count
    assert first_read_count == 24
    assert writes == []
    assert _table_counts(db) == before
    assert set(first) == {
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
    assert "score" not in repr(first)
    assert "suggested_action" not in repr(first)


@pytest.mark.parametrize("candidate_count", [0, 1, 8, 9, 25, 100])
def test_candidate_reader_query_count_is_independent_of_list_size(db, candidate_count):
    from app.services.command_center_service import CommandCenterService

    db.add_all([_opportunity(index) for index in range(candidate_count)])
    db.commit()
    db.expire_all()
    select_count = 0

    def count_selects(_conn, _cursor, statement, _parameters, _context, _many):
        nonlocal select_count
        if statement.lstrip().upper().startswith("SELECT"):
            select_count += 1

    bind = db.get_bind()
    event.listen(bind, "before_cursor_execute", count_selects)
    try:
        rows = CommandCenterService(db).read_opportunity_candidates()
    finally:
        event.remove(bind, "before_cursor_execute", count_selects)

    assert len(rows) == candidate_count
    assert select_count == (1 if candidate_count == 0 else 3)


@pytest.mark.parametrize("candidate_count", [0, 1, 8, 9, 25, 100])
def test_ranked_snapshot_query_count_is_bounded_independently_of_candidates(db, candidate_count):
    from app.services.command_center_service import CommandCenterService

    actor = _actor()
    candidates = [_opportunity(index) for index in range(candidate_count)]
    db.add(actor)
    db.add_all(candidates)
    db.commit()
    db.expire_all()
    db.refresh(actor)
    select_count = 0

    def count_selects(_conn, _cursor, statement, _parameters, _context, _many):
        nonlocal select_count
        if statement.lstrip().upper().startswith("SELECT"):
            select_count += 1

    bind = db.get_bind()
    event.listen(bind, "before_cursor_execute", count_selects)
    try:
        result = CommandCenterService(db).read_snapshot(
            actor=actor,
            as_of=AS_OF,
            since_at=AS_OF - timedelta(days=7),
        )
    finally:
        event.remove(bind, "before_cursor_execute", count_selects)

    assert len(result["today_opportunities"]) == min(candidate_count, 8)
    assert select_count == (24 if candidate_count == 0 else 28)
    assert all("overall_score" not in card for card in result["today_opportunities"])
    assert all("suggested_action" not in card for card in result["today_opportunities"])


def test_full_candidate_set_is_ranked_before_existing_eight_card_limit(db):
    from app.db.models import BreakdownRole
    from app.services.command_center_service import CommandCenterService

    actor = _actor()
    candidates = [_opportunity(index) for index in range(9)]
    for index, candidate in enumerate(candidates):
        candidate.breakdown_roles.append(
            BreakdownRole(
                role_name=candidate.role,
                role_type="Guest Star",
                fit_status="Strong Fit" if index == 8 else "Not Fit",
                fit_score=95 if index == 8 else 5,
                confidence_score=95,
            )
        )
    db.add(actor)
    db.add_all(candidates)
    db.commit()
    before = {
        candidate.id: {
            "visibility_status": candidate.visibility_status,
            "urgency_score": candidate.urgency_score,
            "quality_score": candidate.quality_score,
            "source_metadata": deepcopy(candidate.source_metadata),
        }
        for candidate in candidates
    }

    result = CommandCenterService(db).read_snapshot(
        actor=actor,
        as_of=AS_OF,
        since_at=AS_OF - timedelta(days=7),
    )

    displayed_ids = [card["id"] for card in result["today_opportunities"]]
    assert candidates[8].id in displayed_ids
    assert len(displayed_ids) == 8
    assert candidates[7].id not in displayed_ids
    assert set(result) == {
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
    for candidate in candidates:
        assert {
            "visibility_status": candidate.visibility_status,
            "urgency_score": candidate.urgency_score,
            "quality_score": candidate.quality_score,
            "source_metadata": candidate.source_metadata,
        } == before[candidate.id]


def test_context_batch_uses_latest_actor_opportunity_feedback_and_saved_travel(db):
    from app.db.models import RecommendationFeedback, TravelPreference
    from app.services.command_center_service import CommandCenterService

    actor = _actor()
    candidate = _opportunity(0)
    same_time = AS_OF - timedelta(days=1)
    selected = RecommendationFeedback(
        id=UUID("50000000-0000-0000-0000-000000000001"),
        actor_profile_id=actor.id,
        opportunity_id=candidate.id,
        feedback_type="This Fits Me",
        notes="PRIVATE FEEDBACK NOTE",
        created_at=same_time,
        updated_at=same_time,
    )
    equal_time_higher_id = RecommendationFeedback(
        id=UUID("50000000-0000-0000-0000-000000000002"),
        actor_profile_id=actor.id,
        opportunity_id=candidate.id,
        feedback_type="Not My Type",
        notes="OTHER PRIVATE NOTE",
        created_at=same_time,
        updated_at=same_time,
    )
    db.add_all(
        [
            actor,
            candidate,
            selected,
            equal_time_higher_id,
            TravelPreference(
                actor_profile_id=actor.id,
                audition_max_drive_time=120,
            ),
        ]
    )
    db.commit()

    loaded = CommandCenterService(db).read_opportunity_candidates()
    context = CommandCenterService(db)._read_scoring_contexts(loaded, actor)[candidate.id]

    assert context.feedback_entries[0].key == str(selected.id)
    assert context.feedback_entries[0].feedback_type == "This Fits Me"
    assert context.audition_travel_limit_hours == 2.0
    assert "PRIVATE" not in repr(context)


def test_candidate_reader_preserves_exact_task_7p_inclusion_rules(db):
    from app.services.command_center_service import CommandCenterService

    included = [
        _opportunity(0),
        _opportunity(1, status="archived"),
        _opportunity(2, submission_deadline=AS_OF - timedelta(days=1)),
        _opportunity(3, is_duplicate=True),
    ]
    excluded = [
        _opportunity(10, visibility_status="hidden"),
        _opportunity(11, visibility_status="discarded"),
        _opportunity(12, visibility_status="travel_exception"),
        _opportunity(13, is_demo_data=True),
        _opportunity(14, breakdown_classification="Crew Job"),
    ]
    db.add_all([*included, *excluded])
    db.commit()

    rows = CommandCenterService(db).read_opportunity_candidates()

    assert {row.id for row in rows} == {row.id for row in included}


def test_candidate_reader_preserves_filters_exceeds_eight_and_caps_at_100(db):
    from app.db.models import BreakdownRole, Opportunity, Submission
    from app.services.command_center_service import (
        COMMAND_CENTER_CANDIDATE_LIMIT,
        CommandCenterService,
    )

    candidates = [_opportunity(index) for index in range(105)]
    db.add_all(
        candidates
        + [
            _opportunity(200, visibility_status="hidden"),
            _opportunity(201, is_demo_data=True),
            _opportunity(202, breakdown_classification="Crew Job"),
        ]
    )
    db.flush()
    db.add(BreakdownRole(breakdown_id=candidates[0].id, role_name="Lead"))
    db.commit()
    db.expire_all()

    select_count = 0

    def count_selects(_conn, _cursor, statement, _parameters, _context, _many):
        nonlocal select_count
        if statement.lstrip().upper().startswith("SELECT"):
            select_count += 1

    bind = db.get_bind()
    event.listen(bind, "before_cursor_execute", count_selects)
    try:
        rows = CommandCenterService(db).read_opportunity_candidates()
    finally:
        event.remove(bind, "before_cursor_execute", count_selects)

    assert len(rows) == COMMAND_CENTER_CANDIDATE_LIMIT == 100
    assert len(rows) > 8
    assert [row.role for row in rows[:3]] == ["Role 000", "Role 001", "Role 002"]
    assert all(row.visibility_status == "visible" for row in rows)
    assert all(not row.is_demo_data for row in rows)
    assert all(row.breakdown_classification == "Acting Role" for row in rows)
    assert select_count == 3
    for row in rows:
        state = inspect(row)
        assert state.attrs.breakdown_roles.loaded_value is not NO_VALUE
        assert state.attrs.submissions.loaded_value is not NO_VALUE
    assert db.scalar(select(func.count()).select_from(Opportunity)) == 108
    assert db.scalar(select(func.count()).select_from(BreakdownRole)) == 1
    assert db.scalar(select(func.count()).select_from(Submission)) == 0
