from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.executive_agent import ExecutiveAgent
from app.db.models import (
    ActorProfile,
    AgentRecommendation,
    Asset,
    CareerDevelopmentTask,
    CareerMemory,
    ExecutiveBrief,
    Opportunity,
    Submission,
)
from app.schemas.agent import CareerMemoryUpdate


CALLBACK_STATUSES = {"Requested", "Self-Tape Callback", "In-Person Callback", "Pinned", "Booked"}
MIN_MATERIAL_SUBMISSIONS = 5


class ExecutiveIntelligenceService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_or_create_memory(self, actor: ActorProfile | None) -> CareerMemory:
        memory, created = self.get_or_create_memory_without_commit(actor)
        if created:
            self.db.commit()
            self.db.refresh(memory)
        return memory

    def get_or_create_memory_without_commit(
        self, actor: ActorProfile | None, *, memory_id: UUID | None = None
    ) -> tuple[CareerMemory, bool]:
        actor_id = actor.id if actor else None
        query = select(CareerMemory)
        if memory_id:
            query = query.where(CareerMemory.id == memory_id)
        if actor_id:
            query = query.where(CareerMemory.actor_profile_id == actor_id)
        memory = self.db.scalars(query.order_by(CareerMemory.updated_at.desc()).limit(1)).first()
        if memory:
            return memory, False
        values = {"actor_profile_id": actor_id}
        if memory_id:
            values["id"] = memory_id
        memory = CareerMemory(**values)
        self.db.add(memory)
        return memory, True

    def update_memory(self, actor: ActorProfile | None, payload: CareerMemoryUpdate) -> CareerMemory:
        memory = self.get_or_create_memory(actor)
        data = payload.model_dump(exclude_unset=True)
        if actor and not data.get("actor_profile_id"):
            data["actor_profile_id"] = actor.id
        for key, value in data.items():
            setattr(memory, key, value)
        self.db.commit()
        self.db.refresh(memory)
        return memory

    def list_briefs(self) -> list[ExecutiveBrief]:
        return list(self.db.scalars(select(ExecutiveBrief).order_by(ExecutiveBrief.period_start.desc())))

    def generate_weekly_brief(self, actor: ActorProfile | None = None) -> ExecutiveBrief:
        today = date.today()
        period_start = today - timedelta(days=today.weekday())
        period_end = period_start + timedelta(days=6)
        start_dt = datetime.combine(period_start, datetime.min.time(), tzinfo=timezone.utc)
        end_dt = datetime.combine(period_end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
        actor_id = actor.id if actor else None
        memory = self.get_or_create_memory(actor)

        breakdowns = list(
            self.db.scalars(
                select(Opportunity)
                .where(Opportunity.is_demo_data.is_(False))
                .where(Opportunity.created_at >= start_dt, Opportunity.created_at < end_dt)
                .order_by(Opportunity.created_at.desc())
            )
        )
        submissions = [
            submission
            for submission in self.db.scalars(
                select(Submission)
                .where(Submission.created_at >= start_dt, Submission.created_at < end_dt)
                .order_by(Submission.created_at.desc())
            )
            if not submission.opportunity or not submission.opportunity.is_demo_data
        ]
        callbacks = [item for item in submissions if item.current_status in CALLBACK_STATUSES]
        bookings = [item for item in submissions if item.current_status == "Booked"]
        materials = Counter(asset.asset_name for submission in submissions for asset in submission.assets)
        tasks = list(
            self.db.scalars(
                select(CareerDevelopmentTask)
                .where(CareerDevelopmentTask.updated_at >= start_dt, CareerDevelopmentTask.updated_at < end_dt)
                .order_by(CareerDevelopmentTask.updated_at.desc())
            )
        )
        priorities = ExecutiveAgent(self.db).top_priorities()
        brief = ExecutiveBrief(
            actor_profile_id=actor_id,
            period_start=period_start,
            period_end=period_end,
            brief_type="Weekly",
            new_matching_breakdowns=[self._breakdown_row(item) for item in breakdowns[:10]],
            submissions_completed=[self._submission_row(item) for item in submissions],
            callbacks_received=[self._submission_row(item) for item in callbacks],
            bookings=[self._submission_row(item) for item in bookings],
            materials_used=[{"asset_name": name, "uses": count} for name, count in materials.most_common()],
            career_progress=[{"title": task.title, "status": task.status, "impact": task.estimated_impact} for task in tasks[:10]],
            recommended_priorities=priorities,
            summary=self._summary(memory, breakdowns, submissions, callbacks, bookings, priorities),
        )
        self.db.add(brief)
        self.db.commit()
        self.db.refresh(brief)
        return brief

    def material_performance(self) -> list[dict]:
        assets = list(self.db.scalars(select(Asset).order_by(Asset.asset_type.asc(), Asset.asset_name.asc())))
        recommendations = [
            recommendation
            for recommendation in self.db.scalars(select(AgentRecommendation))
            if not (
                recommendation.opportunity_id
                and (opportunity := self.db.get(Opportunity, recommendation.opportunity_id))
                and opportunity.is_demo_data
            )
        ]
        rows = []
        for asset in assets:
            submissions = [
                submission
                for submission in self.db.scalars(select(Submission))
                if not submission.opportunity or not submission.opportunity.is_demo_data
            ]
            selected = [submission for submission in submissions if any(item.id == asset.id for item in submission.assets)]
            callbacks = [item for item in selected if item.current_status in CALLBACK_STATUSES]
            bookings = [item for item in selected if item.current_status == "Booked"]
            if len(selected) < MIN_MATERIAL_SUBMISSIONS:
                continue
            recommended = sum(
                1
                for recommendation in recommendations
                if asset.id
                in {
                    recommendation.recommended_headshot_id,
                    recommendation.recommended_reel_id,
                    recommendation.recommended_resume_id,
                    recommendation.recommended_slate_id,
                }
            )
            rows.append(
                {
                    "asset_id": asset.id,
                    "asset_name": asset.asset_name,
                    "asset_type": asset.asset_type,
                    "times_recommended": recommended,
                    "times_selected": len(selected),
                    "submissions": len(selected),
                    "callbacks": len(callbacks),
                    "bookings": len(bookings),
                    "callback_rate": round(len(callbacks) / len(selected), 2) if selected else 0,
                    "booking_rate": round(len(bookings) / len(selected), 2) if selected else 0,
                }
            )
        return rows

    def previous_submission_history(self, opportunity: Opportunity) -> dict:
        submissions = [
            submission
            for submission in self.db.scalars(select(Submission).order_by(Submission.created_at.desc()))
            if not submission.opportunity or not submission.opportunity.is_demo_data
        ]
        project = []
        casting_office = []
        production_company = []
        franchise = []
        production_name = str((opportunity.production_details or {}).get("production_company") or "").lower()
        project_tokens = set(opportunity.project.lower().replace(":", " ").split())
        for submission in submissions:
            other = submission.opportunity
            if not other or other.is_demo_data or other.id == opportunity.id:
                continue
            row = self._submission_row(submission)
            if other.project.lower() == opportunity.project.lower():
                project.append(row)
            if opportunity.casting_office_id and other.casting_office_id == opportunity.casting_office_id:
                casting_office.append(row)
            other_company = str((other.production_details or {}).get("production_company") or "").lower()
            if production_name and other_company == production_name:
                production_company.append(row)
            if len(project_tokens.intersection(other.project.lower().replace(":", " ").split())) >= 2:
                franchise.append(row)
        return {
            "this_project": project,
            "this_franchise": franchise,
            "this_casting_office": casting_office,
            "this_production_company": production_company,
        }

    def breakdown_similarity(self, opportunity: Opportunity) -> list[dict]:
        current_terms = self._terms(opportunity)
        rows = []
        for other in self.db.scalars(
            select(Opportunity).where(Opportunity.id != opportunity.id).where(Opportunity.is_demo_data.is_(False))
        ).all():
            terms = self._terms(other)
            shared = sorted(current_terms.intersection(terms))
            if not shared:
                continue
            outcome_bonus = max((self._outcome_weight(item.current_status) for item in other.submissions), default=0)
            score = min(100, len(shared) * 12 + outcome_bonus)
            if score < 18:
                continue
            rows.append(
                {
                    "opportunity_id": other.id,
                    "project": other.project,
                    "role": other.role,
                    "score": score,
                    "shared_signals": shared[:8],
                    "historical_outcomes": [item.current_status for item in other.submissions],
                    "explanation": f"Similar because it shares {', '.join(shared[:5])}.",
                }
            )
        return sorted(rows, key=lambda item: item["score"], reverse=True)[:8]

    def _breakdown_row(self, opportunity: Opportunity) -> dict:
        return {
            "id": str(opportunity.id),
            "project": opportunity.project,
            "role": opportunity.role,
            "project_type": opportunity.project_type,
            "match": opportunity.demographic_match_status,
        }

    def _submission_row(self, submission: Submission) -> dict:
        return {
            "id": str(submission.id),
            "date": submission.submitted_at.isoformat() if submission.submitted_at else submission.created_at.isoformat(),
            "project": submission.opportunity.project if submission.opportunity else None,
            "role": submission.opportunity.role if submission.opportunity else None,
            "materials_used": [asset.asset_name for asset in submission.assets],
            "outcome": submission.current_status,
        }

    def _summary(
        self,
        memory: CareerMemory,
        breakdowns: list[Opportunity],
        submissions: list[Submission],
        callbacks: list[Submission],
        bookings: list[Submission],
        priorities: list[dict],
    ) -> str:
        focus = memory.current_focus or "your active casting goals"
        return (
            f"This week, {len(breakdowns)} new breakdowns were tracked, {len(submissions)} submissions were completed, "
            f"{len(callbacks)} callback-or-better outcomes were recorded, and {len(bookings)} bookings were recorded. "
            f"Executive focus: {focus}. Next priority: {priorities[0]['title'] if priorities else 'add a casting goal'}."
        )

    def _terms(self, opportunity: Opportunity) -> set[str]:
        text = " ".join(
            [
                opportunity.role,
                opportunity.project,
                opportunity.project_type or "",
                opportunity.role_type or "",
                opportunity.category or "",
                opportunity.description,
                str((opportunity.production_details or {}).get("genre") or ""),
                str((opportunity.production_details or {}).get("casting_office") or ""),
                *opportunity.archetypes,
            ]
        ).lower()
        return {part.strip(".,:;()[]") for part in text.split() if len(part.strip(".,:;()[]")) > 3}

    def _outcome_weight(self, status: str) -> int:
        return {
            "Booked": 30,
            "Pinned": 24,
            "In-Person Callback": 20,
            "Self-Tape Callback": 18,
            "Requested": 12,
        }.get(status, 0)
