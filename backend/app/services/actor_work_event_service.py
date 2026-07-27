from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Asset,
    AuditionCalendarEvent,
    CareerDevelopmentTask,
    DailyPlatformCheckIn,
    Opportunity,
    SelfTapeWorkflow,
    Submission,
)
from app.services.journal_service import JournalService, journal_date_from_datetime


class ActorWorkEventService:
    """Central recorder for meaningful actor work.

    Callers should use this instead of directly creating journal/calendar records
    when the event represents actor work across modules.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.journal = JournalService(db)

    def platform_check_in(self, check_in: DailyPlatformCheckIn) -> None:
        platform = (
            check_in.platform_subscription.platform_name
            if check_in.platform_subscription
            else "casting platform"
        )
        self.journal.record_once(
            event_type="Platform Check-In",
            title=f"Checked {platform}",
            description=check_in.notes,
            entry_date=check_in.check_date,
        )

    def accepted_breakdown(self, opportunity: Opportunity) -> None:
        self.journal.record_once(
            event_type="Accepted Breakdown",
            title=f"Accepted {opportunity.role} in {opportunity.project}",
            description=f"{opportunity.project_type or 'Breakdown'} · {opportunity.audition_type}",
            linked_breakdown_id=opportunity.id,
        )
        self._calendar_from_opportunity(opportunity)

    def submission_added(self, submission: Submission) -> None:
        self.journal.record_once(
            event_type="Submitted to Role",
            title=(
                f"Submitted to {submission.opportunity.role} in {submission.opportunity.project}"
                if submission.opportunity
                else "Submitted to role"
            ),
            description=submission.notes,
            entry_date=journal_date_from_datetime(submission.submitted_at),
            linked_breakdown_id=submission.opportunity_id,
            linked_audition_id=submission.id,
        )

    def submission_status_changed(
        self,
        submission: Submission,
        *,
        status: str,
        notes: str | None = None,
        occurred_at: datetime | date | None = None,
    ) -> None:
        status_map = {
            "Self-Tape Callback": "Callback Received",
            "In-Person Callback": "Callback Received",
            "Pinned": "Callback Received",
            "Booked": "Booking Recorded",
            "Passed": "Passed / No Response",
            "No Response": "Passed / No Response",
        }
        event_type = status_map.get(status)
        if not event_type:
            return
        role = submission.opportunity.role if submission.opportunity else "role"
        project = submission.opportunity.project if submission.opportunity else "project"
        self.journal.record_once(
            event_type=event_type,
            title=f"{status}: {role} in {project}",
            description=notes,
            entry_date=journal_date_from_datetime(occurred_at),
            linked_breakdown_id=submission.opportunity_id,
            linked_audition_id=submission.id,
        )

    def self_tape_completed(self, workflow: SelfTapeWorkflow) -> None:
        self.journal.record_once(
            event_type="Self-Tape Completed",
            title=f"Completed self-tape for {workflow.opportunity.role}"
            if workflow.opportunity
            else "Completed self-tape",
            description=workflow.slate_requirements,
            entry_date=journal_date_from_datetime(workflow.updated_at),
            linked_breakdown_id=workflow.opportunity_id,
            linked_audition_id=workflow.submission_id,
        )

    def callback_added(
        self,
        *,
        event_name: str,
        opportunity: Opportunity | None,
        opportunity_id=None,
        submission_id=None,
        notes=None,
        event_datetime=None,
    ) -> None:
        self.journal.record_once(
            event_type="Callback Received",
            title=f"{event_name}: {opportunity.role}" if opportunity else event_name,
            description=notes,
            entry_date=journal_date_from_datetime(event_datetime),
            linked_breakdown_id=opportunity_id,
            linked_audition_id=submission_id,
        )

    def callback_completed(
        self,
        *,
        event_name: str,
        outcome: str | None,
        opportunity_id=None,
        submission_id=None,
        event_datetime=None,
    ) -> None:
        if not outcome:
            return
        self.journal.record_once(
            event_type="Callback Completed",
            title=f"{event_name} completed",
            description=outcome,
            entry_date=journal_date_from_datetime(event_datetime),
            linked_breakdown_id=opportunity_id,
            linked_audition_id=submission_id,
        )

    def material_uploaded(self, asset: Asset, *, career_task_id: UUID | None = None) -> None:
        self.journal.record_once(
            event_type=self._material_event_type(asset),
            title=f"Uploaded {asset.asset_name}",
            description=self._material_description(asset),
            linked_material_id=asset.id,
            linked_career_task_id=career_task_id,
        )

    def resume_updated(self, asset: Asset) -> None:
        self.journal.record_once(
            event_type="Resume Updated",
            title=f"Updated {asset.asset_name}",
            description=asset.description,
            linked_material_id=asset.id,
        )

    def career_task_completed(self, task: CareerDevelopmentTask) -> None:
        self.journal.record_once(
            event_type="Career Task Completed",
            title=f"Completed {task.title}",
            description=task.description,
            linked_career_task_id=task.id,
        )

    def _calendar_from_opportunity(self, opportunity: Opportunity, submission_id=None) -> None:
        if opportunity.audition_type == "Self-Tape" and opportunity.audition_deadline:
            self._calendar_once(
                event_type="Self-Tape Due",
                title=f"Self-tape due: {opportunity.role}",
                start_datetime=opportunity.audition_deadline,
                opportunity_id=opportunity.id,
                submission_id=submission_id,
                location=None,
                is_virtual=True,
                notes=(opportunity.role_details or {}).get("self_tape_submission_link")
                or getattr(opportunity, "submission_method", None),
            )
        elif opportunity.audition_type == "Virtual" and opportunity.audition_deadline:
            self._calendar_once(
                event_type="Virtual Callback",
                title=f"Virtual audition: {opportunity.role}",
                start_datetime=opportunity.audition_deadline,
                opportunity_id=opportunity.id,
                submission_id=submission_id,
                is_virtual=True,
                notes=(opportunity.role_details or {}).get("virtual_audition_link"),
            )
        elif opportunity.audition_type == "In-Person" and opportunity.audition_deadline:
            self._calendar_once(
                event_type="In-Person Callback",
                title=f"In-person audition: {opportunity.role}",
                start_datetime=opportunity.audition_deadline,
                opportunity_id=opportunity.id,
                submission_id=submission_id,
                location=opportunity.audition_location,
                is_virtual=False,
                notes=getattr(opportunity, "submission_method", None),
            )
        if opportunity.callback_date:
            self._calendar_once(
                event_type="Virtual Callback"
                if opportunity.audition_type == "Virtual"
                else "In-Person Callback",
                title=f"Callback: {opportunity.role}",
                start_datetime=opportunity.callback_date,
                opportunity_id=opportunity.id,
                submission_id=submission_id,
                location=opportunity.audition_location,
                is_virtual=opportunity.audition_type == "Virtual",
            )

    def _calendar_once(self, **values) -> AuditionCalendarEvent:
        statement = (
            select(AuditionCalendarEvent)
            .where(AuditionCalendarEvent.event_type == values["event_type"])
            .where(AuditionCalendarEvent.start_datetime == values["start_datetime"])
        )
        if values.get("opportunity_id"):
            statement = statement.where(
                AuditionCalendarEvent.opportunity_id == values["opportunity_id"]
            )
        if values.get("submission_id"):
            statement = statement.where(
                AuditionCalendarEvent.submission_id == values["submission_id"]
            )
        existing = self.db.scalar(statement)
        if existing:
            return existing
        event = AuditionCalendarEvent(**values)
        self.db.add(event)
        return event

    def _material_event_type(self, asset: Asset) -> str:
        if asset.asset_type == "Headshot":
            return "Headshot Uploaded"
        if asset.asset_type == "Reel":
            return "Reel Uploaded"
        if asset.asset_type == "Slate":
            return "Slate Uploaded"
        if asset.asset_type == "Resume":
            return "Resume Updated"
        return "Material Uploaded"

    def _material_description(self, asset: Asset) -> str | None:
        if asset.asset_type == "Reel" and asset.archetype_names:
            return f"Scene/material for {', '.join(asset.archetype_names)}."
        if asset.archetype_names:
            return f"Archetypes: {', '.join(asset.archetype_names)}."
        return asset.description
