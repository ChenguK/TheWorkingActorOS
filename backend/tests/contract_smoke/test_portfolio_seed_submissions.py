from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.core.config import Settings
from app.db.models import (
    ActorJournalEntry,
    AgentRecommendation,
    Asset,
    AuditionCalendarEvent,
    AuditionJournalEntry,
    CallbackEvent,
    Opportunity,
    RecommendationFeedback,
    Submission,
    SubmissionStatusHistory,
)
from app.services.sanitized_portfolio_manifest import (
    OPPORTUNITY_IDS,
    SUBMISSION_IDS,
    build_sanitized_portfolio_manifest,
)
from app.services.sanitized_portfolio_submission_service import (
    SanitizedPortfolioSubmissionService,
)
from app.services.submission_service import SubmissionService
from scripts.seed_sanitized_portfolio import run


pytestmark = pytest.mark.contract_smoke
AS_OF_A = datetime(2034, 6, 3, 15, 0, tzinfo=timezone.utc)
AS_OF_B = AS_OF_A + timedelta(days=45)


def settings() -> Settings:
    return Settings(
        _env_file=None,
        environment="development",
        sanitized_portfolio_seed_enabled=True,
    )


def counts(session) -> tuple[int, int, int, int, int]:
    return tuple(
        session.scalar(select(func.count()).select_from(model))
        for model in (
            Submission,
            SubmissionStatusHistory,
            AuditionCalendarEvent,
            AuditionJournalEntry,
            ActorJournalEntry,
        )
    )


def test_submission_workflow_is_durable_idempotent_stable_and_resettable(db) -> None:
    from app.core.database import SessionLocal

    db.close()
    run(execute=True, reset=False, settings=settings(), session_factory=SessionLocal, as_of=AS_OF_A)
    with SessionLocal() as fresh:
        assert counts(fresh) == (3, 3, 10, 3, 3)
        submitted_at = {
            item_id: fresh.get(Submission, item_id).submitted_at for item_id in SUBMISSION_IDS
        }
        assert [fresh.get(Submission, item_id).current_status for item_id in SUBMISSION_IDS] == [
            "Submitted",
            "Requested",
            "Booked",
        ]
        events = list(fresh.scalars(select(AuditionCalendarEvent)))
        assert all(event.submission_id in SUBMISSION_IDS for event in events)
        assert all(event.opportunity_id in OPPORTUNITY_IDS for event in events)
        assert {event.event_type for event in events} == {
            "Submission Due",
            "Self-Tape Due",
            "Virtual Callback",
            "In-Person Callback",
            "Shoot",
        }

    run(execute=True, reset=False, settings=settings(), session_factory=SessionLocal, as_of=AS_OF_B)
    with SessionLocal() as fresh:
        assert counts(fresh) == (3, 3, 10, 3, 3)
        assert {
            item_id: fresh.get(Submission, item_id).submitted_at for item_id in SUBMISSION_IDS
        } == submitted_at
        assert fresh.scalar(select(func.count()).select_from(AgentRecommendation)) == 1
        assert fresh.scalar(select(func.count()).select_from(RecommendationFeedback)) == 1
        assert fresh.scalar(select(func.count()).select_from(Asset)) == 0
        assert fresh.scalar(select(func.count()).select_from(CallbackEvent)) == 0

        SanitizedPortfolioSubmissionService(fresh).reset(
            build_sanitized_portfolio_manifest(AS_OF_B)
        )
        fresh.commit()

    with SessionLocal() as fresh:
        assert counts(fresh) == (0, 0, 0, 0, 0)
        assert fresh.scalar(select(func.count()).select_from(Opportunity)) == 7


def test_failure_before_third_submission_rolls_back_all_workflow_rows(db, monkeypatch) -> None:
    from app.core.database import SessionLocal

    db.close()
    original = SubmissionService.create_without_commit
    calls = 0

    def fail_third(self, payload, *, submission_id=None):
        nonlocal calls
        calls += 1
        if calls == 3:
            raise RuntimeError("forced third Submission failure")
        return original(self, payload, submission_id=submission_id)

    monkeypatch.setattr(SubmissionService, "create_without_commit", fail_third)
    with pytest.raises(RuntimeError, match="forced third Submission failure"):
        run(
            execute=True,
            reset=False,
            settings=settings(),
            session_factory=SessionLocal,
            as_of=AS_OF_A,
        )

    with SessionLocal() as fresh:
        assert counts(fresh) == (0, 0, 0, 0, 0)
        assert fresh.scalar(select(func.count()).select_from(Opportunity)) == 0
