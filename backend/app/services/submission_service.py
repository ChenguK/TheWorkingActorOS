from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.db.models import Asset, Submission, SubmissionStatusHistory
from app.repositories.submission import SubmissionRepository
from app.schemas.submission import (
    SUBMISSION_STATUSES,
    SubmissionCreate,
    SubmissionStatusHistoryCreate,
    SubmissionUpdate,
)
from app.services.actor_work_event_service import ActorWorkEventService
from app.services.workflow_connector_service import WorkflowConnectorService


class SubmissionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = SubmissionRepository(db)

    def list(self) -> list[Submission]:
        return self.repo.list_full()

    def waiting(self) -> list[Submission]:
        return [
            item
            for item in self.repo.list_full()
            if item.current_status in {"Submitted", "No Response"}
        ]

    def get(self, submission_id) -> Submission:
        return self.repo.get_full(submission_id)

    def _load_assets(self, asset_ids) -> list[Asset]:
        assets = []
        for asset_id in asset_ids:
            asset = self.db.get(Asset, asset_id)
            if not asset:
                raise NotFoundError(f"Asset {asset_id} not found")
            assets.append(asset)
        return assets

    def create(self, payload: SubmissionCreate) -> Submission:
        if payload.current_status not in SUBMISSION_STATUSES:
            raise ValueError("Invalid submission status")
        submission = Submission(
            actor_profile_id=payload.actor_profile_id,
            opportunity_id=payload.opportunity_id,
            current_status=payload.current_status,
            notes=payload.notes,
            submitted_at=payload.submitted_at,
            submission_fee=payload.submission_fee,
            media_fee=payload.media_fee,
            travel_cost=payload.travel_cost,
            housing_cost=payload.housing_cost,
            parking_cost=payload.parking_cost,
            other_cost=payload.other_cost,
            total_cost=self._total_cost(payload),
        )
        submission.assets = self._load_assets(payload.asset_ids)
        for asset in submission.assets:
            asset.last_used_date = (payload.submitted_at or datetime.utcnow()).date()
        submission.status_history.append(
            SubmissionStatusHistory(
                status=payload.current_status,
                notes="Initial submission status",
                occurred_at=payload.submitted_at or datetime.utcnow(),
            )
        )
        self.db.add(submission)
        self.db.flush()
        WorkflowConnectorService(self.db).after_submission_created(submission)
        ActorWorkEventService(self.db).submission_added(submission)
        self.db.commit()
        return self.repo.get_full(submission.id)

    def update(self, submission_id, payload: SubmissionUpdate) -> Submission:
        submission = self.repo.get_full(submission_id)
        data = payload.model_dump(exclude_unset=True, exclude={"asset_ids"})
        for key, value in data.items():
            setattr(submission, key, value)
        if payload.asset_ids is not None:
            submission.assets = self._load_assets(payload.asset_ids)
        self._recalculate_total(submission)
        self.db.commit()
        return self.repo.get_full(submission.id)

    def add_status(self, submission_id, payload: SubmissionStatusHistoryCreate) -> Submission:
        if payload.status not in SUBMISSION_STATUSES:
            raise ValueError("Invalid submission status")
        submission = self.repo.get_full(submission_id)
        submission.current_status = payload.status
        submission.status_history.append(
            SubmissionStatusHistory(
                status=payload.status,
                notes=payload.notes,
                occurred_at=payload.occurred_at or datetime.utcnow(),
            )
        )
        WorkflowConnectorService(self.db).after_submission_status_changed(submission)
        ActorWorkEventService(self.db).submission_status_changed(
            submission,
            status=payload.status,
            notes=payload.notes,
            occurred_at=payload.occurred_at,
        )
        self.db.commit()
        return self.repo.get_full(submission.id)

    def delete(self, submission_id) -> None:
        submission = self.repo.get(submission_id)
        self.repo.delete(submission)
        self.db.commit()

    def _total_cost(self, payload: SubmissionCreate) -> float:
        return sum(
            [
                payload.submission_fee,
                payload.media_fee,
                payload.travel_cost,
                payload.housing_cost,
                payload.parking_cost,
                payload.other_cost,
            ]
        )

    def _recalculate_total(self, submission: Submission) -> None:
        submission.total_cost = sum(
            [
                float(submission.submission_fee or 0),
                float(submission.media_fee or 0),
                float(submission.travel_cost or 0),
                float(submission.housing_cost or 0),
                float(submission.parking_cost or 0),
                float(submission.other_cost or 0),
            ]
        )
