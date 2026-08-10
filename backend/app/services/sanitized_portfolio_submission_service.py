from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models import (
    ActorJournalEntry,
    ActorProfile,
    AuditionCalendarEvent,
    AuditionJournalEntry,
    Opportunity,
    Submission,
    SubmissionStatusHistory,
)
from app.schemas.submission import SubmissionCreate
from app.services.portfolio_seed_ownership_service import (
    PORTFOLIO_PROFILE_ID,
    PORTFOLIO_PROFILE_NAME,
    PortfolioSeedOwnershipService,
)
from app.services.sanitized_portfolio_manifest import SanitizedPortfolioManifest
from app.services.submission_service import SubmissionService


SubmissionSeedAction = Literal["create", "unchanged"]
PORTFOLIO_SUBMISSION_COLLISION_ERROR = (
    "reserved sanitized portfolio Submission identity is already in use"
)
PORTFOLIO_SUBMISSION_RESET_AMBIGUITY_ERROR = (
    "portfolio Submission reset found an ambiguous derived workflow record"
)


@dataclass(frozen=True)
class SubmissionSeedItemPlan:
    id: UUID
    opportunity_id: UUID
    action: SubmissionSeedAction


@dataclass(frozen=True)
class SubmissionSeedPlan:
    manifest: SanitizedPortfolioManifest
    items: tuple[SubmissionSeedItemPlan, ...]

    @property
    def create_count(self) -> int:
        return sum(item.action == "create" for item in self.items)

    @property
    def unchanged_count(self) -> int:
        return sum(item.action == "unchanged" for item in self.items)


class SanitizedPortfolioSubmissionService:
    """Plans and composes manifest Submission roots without committing."""

    def __init__(self, db: Session):
        self.db = db

    def plan(
        self,
        manifest: SanitizedPortfolioManifest,
        *,
        allow_planned_actor_create: bool = False,
        allow_planned_opportunity_create: bool = False,
    ) -> SubmissionSeedPlan:
        actor = self.db.get(ActorProfile, PORTFOLIO_PROFILE_ID)
        if actor is None:
            if not allow_planned_actor_create:
                raise ValueError("sanitized portfolio ActorProfile must exist before Submissions")
        elif actor.name != PORTFOLIO_PROFILE_NAME:
            raise ValueError("sanitized portfolio ActorProfile must exist before Submissions")
        opportunity_ids = {item.id for item in manifest.opportunities}
        opportunities = {
            item.id: item
            for item in self.db.scalars(
                select(Opportunity).where(Opportunity.id.in_(opportunity_ids))
            ).all()
        }
        if not allow_planned_opportunity_create:
            for opportunity_id in opportunity_ids:
                opportunity = opportunities.get(opportunity_id)
                if opportunity is None or not PortfolioSeedOwnershipService.is_portfolio_owned(
                    opportunity
                ):
                    raise ValueError("portfolio Submission Opportunity prerequisite is missing")
        submission_ids = tuple(item.id for item in manifest.submissions)
        existing = {
            item.id: item
            for item in self.db.scalars(
                select(Submission).where(Submission.id.in_(submission_ids))
            ).all()
        }
        items = []
        for definition in manifest.submissions:
            record = existing.get(definition.id)
            if record is not None and not self._is_owned(
                record, definition.opportunity_id, opportunities
            ):
                raise ValueError(PORTFOLIO_SUBMISSION_COLLISION_ERROR)
            items.append(
                SubmissionSeedItemPlan(
                    definition.id,
                    definition.opportunity_id,
                    "unchanged" if record else "create",
                )
            )
        return SubmissionSeedPlan(manifest, tuple(items))

    def apply(self, plan: SubmissionSeedPlan) -> None:
        definitions = {item.id: item for item in plan.manifest.submissions}
        for item in plan.items:
            if item.action != "create":
                continue
            definition = definitions[item.id]
            SubmissionService(self.db).create_without_commit(
                SubmissionCreate(
                    actor_profile_id=PORTFOLIO_PROFILE_ID,
                    opportunity_id=definition.opportunity_id,
                    current_status=definition.current_status,
                    submitted_at=definition.submitted_at,
                ),
                submission_id=definition.id,
            )

    def reset(self, manifest: SanitizedPortfolioManifest) -> None:
        submission_ids = tuple(item.id for item in manifest.submissions)
        opportunity_ids = tuple(item.opportunity_id for item in manifest.submissions)
        submissions = list(
            self.db.scalars(select(Submission).where(Submission.id.in_(submission_ids))).all()
        )
        for submission in submissions:
            expected = next(item for item in manifest.submissions if item.id == submission.id)
            if (
                submission.actor_profile_id != PORTFOLIO_PROFILE_ID
                or submission.opportunity_id != expected.opportunity_id
            ):
                raise ValueError(PORTFOLIO_SUBMISSION_COLLISION_ERROR)

        calendars = list(
            self.db.scalars(
                select(AuditionCalendarEvent).where(
                    or_(
                        AuditionCalendarEvent.submission_id.in_(submission_ids),
                        AuditionCalendarEvent.opportunity_id.in_(opportunity_ids),
                    )
                )
            ).all()
        )
        audition_journals = list(
            self.db.scalars(
                select(AuditionJournalEntry).where(
                    or_(
                        AuditionJournalEntry.submission_id.in_(submission_ids),
                        AuditionJournalEntry.opportunity_id.in_(opportunity_ids),
                    )
                )
            ).all()
        )
        actor_journals = list(
            self.db.scalars(
                select(ActorJournalEntry).where(
                    or_(
                        ActorJournalEntry.linked_audition_id.in_(submission_ids),
                        ActorJournalEntry.linked_breakdown_id.in_(opportunity_ids),
                    )
                )
            ).all()
        )
        self._require_unambiguous(calendars, submission_ids, opportunity_ids)
        self._require_unambiguous(audition_journals, submission_ids, opportunity_ids)
        self._require_unambiguous(actor_journals, submission_ids, opportunity_ids)
        for record in (*calendars, *audition_journals, *actor_journals):
            self.db.delete(record)
        histories = list(
            self.db.scalars(
                select(SubmissionStatusHistory).where(
                    SubmissionStatusHistory.submission_id.in_(submission_ids)
                )
            ).all()
        )
        for record in histories:
            self.db.delete(record)
        for submission in submissions:
            self.db.delete(submission)
        self.db.flush()

    @staticmethod
    def _is_owned(
        submission: Submission,
        expected_opportunity_id: UUID,
        opportunities: dict[UUID, Opportunity],
    ) -> bool:
        opportunity = opportunities.get(expected_opportunity_id)
        return (
            submission.actor_profile_id == PORTFOLIO_PROFILE_ID
            and submission.opportunity_id == expected_opportunity_id
            and opportunity is not None
            and PortfolioSeedOwnershipService.is_portfolio_owned(opportunity)
        )

    @staticmethod
    def _require_unambiguous(records, submission_ids, opportunity_ids) -> None:
        for record in records:
            submission_id = getattr(record, "submission_id", None) or getattr(
                record, "linked_audition_id", None
            )
            opportunity_id = getattr(record, "opportunity_id", None) or getattr(
                record, "linked_breakdown_id", None
            )
            if submission_id is not None and submission_id not in submission_ids:
                raise ValueError(PORTFOLIO_SUBMISSION_RESET_AMBIGUITY_ERROR)
            if opportunity_id is not None and opportunity_id not in opportunity_ids:
                raise ValueError(PORTFOLIO_SUBMISSION_RESET_AMBIGUITY_ERROR)
