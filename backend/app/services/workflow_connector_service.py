from __future__ import annotations

from datetime import date, datetime, time, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.learning_agent import LearningAgent
from app.db.models import (
    ActorProfile,
    ActorRelationship,
    AgentRecommendation,
    Asset,
    AuditionCalendarEvent,
    AuditionJournalEntry,
    CareerDevelopmentTask,
    CastingGoal,
    DreamRoleTarget,
    Opportunity,
    Submission,
    WatchList,
)


POSITIVE_OUTCOME_STATUSES = {"Requested", "Self-Tape Callback", "In-Person Callback", "Pinned", "Booked"}


class WorkflowConnectorService:
    """Keeps cross-module workflow records connected without duplicating domain models."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def after_submission_created(self, submission: Submission) -> None:
        opportunity = submission.opportunity or self.db.get(Opportunity, submission.opportunity_id)
        if not opportunity:
            return
        self._record_strategy_materials(opportunity)
        self._ensure_calendar_events(opportunity, submission)
        self._ensure_journal_entry(opportunity, submission)
        self._link_relationships(opportunity, submission)
        self._record_submission_link(opportunity, submission)

    def after_submission_status_changed(self, submission: Submission) -> None:
        opportunity = submission.opportunity or self.db.get(Opportunity, submission.opportunity_id)
        if opportunity:
            self._record_outcome(opportunity, submission)
            self._link_relationships(opportunity, submission)
        actor = self.db.get(ActorProfile, submission.actor_profile_id)
        if actor:
            LearningAgent(self.db).analyze(actor)

    def after_asset_created(self, asset: Asset, career_task_id: UUID | None = None) -> None:
        if not career_task_id:
            return
        task = self.db.get(CareerDevelopmentTask, career_task_id)
        if not task:
            return
        task.asset_id = asset.id
        task.status = self._task_completion_status(task, asset)
        if task.status == "Completed":
            task.completed_at = datetime.now(timezone.utc)
        task.reason = self._append_note(
            task.reason,
            f"Material linked: {asset.asset_name} ({asset.asset_type}).",
        )

    def after_casting_goal_saved(self, goal: CastingGoal) -> None:
        terms = self._clean_terms(
            [
                goal.title,
                goal.goal_type,
                *goal.target_archetypes,
                *goal.target_role_types,
                *goal.target_project_types,
                *goal.target_markets,
                *goal.target_casting_offices,
            ]
        )
        if not terms or goal.status != "Active":
            return
        self._upsert_watch_list(
            actor_profile_id=goal.actor_profile_id,
            title=f"Casting Goal: {goal.title}",
            category="Casting Goals",
            terms=terms,
            priority=goal.priority,
            notes="Automatically suggested from an active Casting Goal.",
        )

    def after_dream_target_saved(self, actor: ActorProfile, target: DreamRoleTarget) -> None:
        terms = self._clean_terms(
            [
                target.name,
                target.target_type,
                target.description,
                target.notes,
                *target.target_archetypes,
                *target.target_genres,
                *target.target_offices,
            ]
        )
        if not terms:
            return
        self._upsert_watch_list(
            actor_profile_id=actor.id,
            title=f"Dream Role: {target.name}",
            category=target.target_type,
            terms=terms,
            priority="High",
            notes="Automatically suggested from a Dream Role target.",
        )

    def profile_changed(self, actor: ActorProfile, changed_fields: set[str]) -> None:
        watched = {
            "playable_age_min",
            "playable_age_max",
            "secondary_playable_age_min",
            "secondary_playable_age_max",
            "current_location",
            "skills",
            "ethnicities",
            "racial_identities",
            "gender_identities",
            "gender_expression",
            "included_role_types",
            "excluded_role_types",
        }
        if not changed_fields.intersection(watched):
            return
        for opportunity in self.db.scalars(select(Opportunity).where(Opportunity.is_demo_data.is_(False))).all():
            opportunity.source_metadata = {
                **(opportunity.source_metadata or {}),
                "rescore_recommended": True,
                "rescore_reason": "Actor profile settings changed.",
                "rescore_triggered_by_fields": sorted(changed_fields.intersection(watched)),
            }

    def _record_strategy_materials(self, opportunity: Opportunity) -> None:
        recommendation = self.db.scalars(
            select(AgentRecommendation)
            .where(AgentRecommendation.opportunity_id == opportunity.id)
            .order_by(AgentRecommendation.created_at.desc())
            .limit(1)
        ).first()
        if not recommendation:
            return
        material_ids = {
            "headshot": str(recommendation.recommended_headshot_id) if recommendation.recommended_headshot_id else None,
            "reel": str(recommendation.recommended_reel_id) if recommendation.recommended_reel_id else None,
            "resume": str(recommendation.recommended_resume_id) if recommendation.recommended_resume_id else None,
            "slate": str(recommendation.recommended_slate_id) if recommendation.recommended_slate_id else None,
        }
        opportunity.ai_inference = {
            **(opportunity.ai_inference or {}),
            "strategy_recommended_material_ids": {key: value for key, value in material_ids.items() if value},
            "strategy_recommendation_id": str(recommendation.id),
        }

    def _ensure_calendar_events(self, opportunity: Opportunity, submission: Submission) -> None:
        for event_type, starts_at, location, is_virtual in self._calendar_candidates(opportunity):
            if not starts_at:
                continue
            self._create_event_once(
                title=f"{event_type}: {opportunity.role} · {opportunity.project}",
                event_type=event_type,
                opportunity_id=opportunity.id,
                submission_id=submission.id,
                starts_at=starts_at,
                location=location,
                is_virtual=is_virtual,
                notes=self._event_notes(opportunity),
            )

    def _calendar_candidates(self, opportunity: Opportunity) -> list[tuple[str, datetime | None, str | None, bool]]:
        role_details = opportunity.role_details or {}
        production = opportunity.production_details or {}
        source = opportunity.source_metadata or {}
        is_virtual = opportunity.audition_type == "Virtual" or bool(
            source.get("virtual_audition_link") or role_details.get("virtual_audition_link")
        )
        return [
            ("Submission Due", opportunity.submission_deadline, None, False),
            (
                "Self-Tape Due" if opportunity.audition_type == "Self-Tape" else "Virtual Callback" if is_virtual else "In-Person Callback",
                opportunity.audition_deadline,
                opportunity.audition_location or self._string(role_details.get("audition_location_name")) or None,
                is_virtual,
            ),
            (
                "Virtual Callback" if is_virtual else "In-Person Callback",
                opportunity.callback_date,
                opportunity.audition_location or self._string(role_details.get("audition_location_name")) or None,
                is_virtual,
            ),
            (
                "Shoot",
                self._date_to_datetime(opportunity.shoot_start_date),
                opportunity.shoot_location or opportunity.location or self._string(production.get("performance_location")),
                False,
            ),
            (
                "Shoot",
                self._parse_datetime(production.get("performance_date")),
                self._string(production.get("performance_location")) or opportunity.location,
                False,
            ),
        ]

    def _create_event_once(
        self,
        *,
        title: str,
        event_type: str,
        opportunity_id: UUID,
        submission_id: UUID,
        starts_at: datetime,
        location: str | None,
        is_virtual: bool,
        notes: str | None,
    ) -> None:
        existing = self.db.scalars(
            select(AuditionCalendarEvent)
            .where(AuditionCalendarEvent.opportunity_id == opportunity_id)
            .where(AuditionCalendarEvent.submission_id == submission_id)
            .where(AuditionCalendarEvent.event_type == event_type)
            .where(AuditionCalendarEvent.start_datetime == starts_at)
        ).first()
        if existing:
            return
        self.db.add(
            AuditionCalendarEvent(
                title=title,
                event_type=event_type,
                opportunity_id=opportunity_id,
                submission_id=submission_id,
                start_datetime=starts_at,
                location=location,
                is_virtual=is_virtual,
                notes=notes,
            )
        )

    def _ensure_journal_entry(self, opportunity: Opportunity, submission: Submission) -> None:
        existing = self.db.scalars(
            select(AuditionJournalEntry).where(AuditionJournalEntry.submission_id == submission.id)
        ).first()
        if existing:
            return
        self.db.add(
            AuditionJournalEntry(
                submission_id=submission.id,
                opportunity_id=opportunity.id,
                date=date.today(),
                preparation_notes=self._event_notes(opportunity),
                casting_notes=self._string((opportunity.production_details or {}).get("casting_office")),
                follow_up_notes=self._submission_links(opportunity),
            )
        )

    def _link_relationships(self, opportunity: Opportunity, submission: Submission) -> None:
        office_name = self._string((opportunity.production_details or {}).get("casting_office"))
        contact_name = self._string((opportunity.role_details or {}).get("casting_contact")) or self._string(
            (opportunity.source_metadata or {}).get("casting_contact")
        )
        if opportunity.casting_office:
            office_name = opportunity.casting_office.name
        if opportunity.casting_contact:
            contact_name = opportunity.casting_contact.name
        for relationship in self.db.scalars(select(ActorRelationship)).all():
            company = (relationship.company_office or "").strip().lower()
            name = relationship.name.strip().lower()
            if not (
                office_name and company and office_name.lower() == company
                or contact_name and name and contact_name.lower() == name
            ):
                continue
            if opportunity not in relationship.linked_opportunities:
                relationship.linked_opportunities.append(opportunity)
            if submission not in relationship.linked_submissions:
                relationship.linked_submissions.append(submission)
            if submission.current_status in POSITIVE_OUTCOME_STATUSES and submission.current_status not in relationship.linked_outcomes:
                relationship.linked_outcomes = [*(relationship.linked_outcomes or []), submission.current_status]

    def _record_submission_link(self, opportunity: Opportunity, submission: Submission) -> None:
        existing = list((opportunity.source_metadata or {}).get("linked_submission_ids") or [])
        submission_id = str(submission.id)
        if submission_id not in existing:
            existing.append(submission_id)
        opportunity.source_metadata = {**(opportunity.source_metadata or {}), "linked_submission_ids": existing}

    def _record_outcome(self, opportunity: Opportunity, submission: Submission) -> None:
        outcomes = list((opportunity.source_metadata or {}).get("outcome_history") or [])
        outcomes.append(
            {
                "submission_id": str(submission.id),
                "status": submission.current_status,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        opportunity.source_metadata = {**(opportunity.source_metadata or {}), "outcome_history": outcomes}

    def _upsert_watch_list(
        self,
        *,
        actor_profile_id: UUID | None,
        title: str,
        category: str,
        terms: list[str],
        priority: str,
        notes: str,
    ) -> WatchList:
        existing = self.db.scalars(select(WatchList).where(WatchList.title == title)).first()
        if existing:
            existing.actor_profile_id = actor_profile_id
            existing.category = category
            existing.terms = terms
            existing.priority = priority if priority in {"Low", "Medium", "High"} else "Medium"
            existing.enabled = True
            existing.notes = notes
            return existing
        record = WatchList(
            actor_profile_id=actor_profile_id,
            title=title,
            category=category,
            terms=terms,
            enabled=True,
            priority=priority if priority in {"Low", "Medium", "High"} else "Medium",
            notes=notes,
        )
        self.db.add(record)
        return record

    def _task_completion_status(self, task: CareerDevelopmentTask, asset: Asset) -> str:
        text = f"{task.title} {task.description} {task.reason or ''}".lower()
        if asset.asset_type.lower() in text or any(archetype.lower() in text for archetype in asset.archetype_names):
            return "Completed"
        return "Partially Completed"

    def _event_notes(self, opportunity: Opportunity) -> str | None:
        role_details = opportunity.role_details or {}
        values = [
            self._string(role_details.get("preparation")),
            self._string(role_details.get("preparation_instructions")),
            self._string(role_details.get("submission_instructions")),
        ]
        return "\n".join(value for value in values if value) or None

    def _submission_links(self, opportunity: Opportunity) -> str | None:
        source = opportunity.source_metadata or {}
        role = opportunity.role_details or {}
        values = [
            self._string(source.get("self_tape_submission_link")),
            self._string(role.get("self_tape_submission_link")),
            self._string(source.get("submission_link")),
            self._string(source.get("virtual_audition_link")),
            self._string(role.get("virtual_audition_link")),
        ]
        return "\n".join(value for value in values if value) or None

    def _append_note(self, current: str | None, note: str) -> str:
        return "\n".join(item for item in [current, note] if item)

    def _clean_terms(self, values: list[str | None]) -> list[str]:
        seen = set()
        terms = []
        for value in values:
            for part in str(value or "").replace("/", ",").split(","):
                term = part.strip()
                key = term.lower()
                if term and key not in seen:
                    seen.add(key)
                    terms.append(term)
        return terms

    def _date_to_datetime(self, value: date | None) -> datetime | None:
        if not value:
            return None
        return datetime.combine(value, time(hour=9), tzinfo=timezone.utc)

    def _parse_datetime(self, value: object) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return self._date_to_datetime(value)
        if not isinstance(value, str) or not value.strip():
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

    def _string(self, value: object) -> str:
        if value is None or value is False:
            return ""
        if isinstance(value, list):
            return ", ".join(str(item) for item in value if item)
        if isinstance(value, dict):
            return ", ".join(f"{key}: {item}" for key, item in value.items() if item)
        return str(value).strip()
