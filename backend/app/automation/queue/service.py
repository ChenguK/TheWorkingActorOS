from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.automation.submission.adapters import SubmissionAdapterRegistry
from app.core.errors import NotFoundError, ValidationError
from app.db.models import AgentRecommendation, SubmissionAutomationQueue


class SubmissionAutomationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.adapters = SubmissionAdapterRegistry()

    def queue_from_recommendation(self, recommendation_id) -> SubmissionAutomationQueue:
        recommendation = self.db.get(AgentRecommendation, recommendation_id)
        if not recommendation:
            raise NotFoundError("Recommendation not found")
        adapter = self.adapters.choose(recommendation)
        prepared = adapter.prepare(recommendation)
        queue_item = SubmissionAutomationQueue(
            opportunity_id=recommendation.opportunity_id,
            recommendation_id=recommendation.id,
            adapter_key=adapter.adapter_key,
            submission_mode=adapter.submission_mode,
            approval_status="Pending Approval",
            automation_status="Prepared",
            prepared_payload=prepared,
        )
        self.db.add(queue_item)
        self.db.commit()
        self.db.refresh(queue_item)
        return queue_item

    def approve(self, queue_id) -> SubmissionAutomationQueue:
        item = self._get(queue_id)
        item.approval_status = "Approved"
        item.approved_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(item)
        return item

    def reject(self, queue_id) -> SubmissionAutomationQueue:
        item = self._get(queue_id)
        item.approval_status = "Rejected"
        item.automation_status = "Cancelled"
        self.db.commit()
        self.db.refresh(item)
        return item

    def execute(self, queue_id) -> SubmissionAutomationQueue:
        item = self._get(queue_id)
        if item.approval_status != "Approved":
            raise ValidationError("Submission automation requires user approval before execution")
        if item.automation_status == "Completed":
            return item
        adapter = self.adapters.get(item.adapter_key)
        try:
            item.automation_status = "Running"
            item.execution_log = adapter.execute(item.prepared_payload)
            item.automation_status = "Completed"
            item.executed_at = datetime.utcnow()
        except Exception as exc:
            item.retry_count += 1
            item.error_message = str(exc)
            item.automation_status = "Retry Ready" if item.retry_count < item.max_retries else "Failed"
        self.db.commit()
        self.db.refresh(item)
        return item

    def list(self) -> list[SubmissionAutomationQueue]:
        return list(
            self.db.scalars(
                select(SubmissionAutomationQueue).order_by(SubmissionAutomationQueue.created_at.desc())
            )
        )

    def _get(self, queue_id) -> SubmissionAutomationQueue:
        item = self.db.get(SubmissionAutomationQueue, queue_id)
        if not item:
            raise NotFoundError("Submission queue item not found")
        return item
