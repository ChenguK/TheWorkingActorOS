from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import UUID

from app.db.models import Submission
from app.schemas.submission import SubmissionCreate
from app.services.submission_service import SubmissionService


SUBMISSION_ID = UUID("40000000-0000-0000-0000-000000000001")


def payload() -> SubmissionCreate:
    return SubmissionCreate(
        actor_profile_id=UUID("10000000-0000-0000-0000-000000000001"),
        opportunity_id=UUID("20000000-0000-0000-0000-000000000001"),
        current_status="Submitted",
        submitted_at=datetime(2034, 1, 2, 12, 0, tzinfo=timezone.utc),
    )


def test_noncommitting_create_preserves_workflow_and_does_not_commit(monkeypatch) -> None:
    db = MagicMock()
    service = SubmissionService(db)
    service._load_assets = MagicMock(return_value=[])
    connector = MagicMock()
    work_events = MagicMock()
    monkeypatch.setattr(
        "app.services.submission_service.WorkflowConnectorService",
        lambda database: connector,
    )
    monkeypatch.setattr(
        "app.services.submission_service.ActorWorkEventService",
        lambda database: work_events,
    )

    submission = service.create_without_commit(payload(), submission_id=SUBMISSION_ID)

    assert isinstance(submission, Submission)
    assert submission.id == SUBMISSION_ID
    assert len(submission.status_history) == 1
    db.add.assert_called_once_with(submission)
    db.flush.assert_called_once_with()
    connector.after_submission_created.assert_called_once_with(submission)
    work_events.submission_added.assert_called_once_with(submission)
    db.commit.assert_not_called()


def test_public_create_still_commits_once_and_returns_repository_result(monkeypatch) -> None:
    db = MagicMock()
    service = SubmissionService(db)
    created = Submission(id=SUBMISSION_ID)
    returned = MagicMock()
    monkeypatch.setattr(service, "create_without_commit", MagicMock(return_value=created))
    service.repo.get_full = MagicMock(return_value=returned)

    assert service.create(payload()) is returned
    db.commit.assert_called_once_with()
    service.repo.get_full.assert_called_once_with(SUBMISSION_ID)
