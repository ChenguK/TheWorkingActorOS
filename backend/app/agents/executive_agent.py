from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    ActorRelationship,
    AgentRecommendation,
    AuditionCalendarEvent,
    CareerMemory,
    CareerDevelopmentTask,
    CastingGoal,
    LearningInsight,
    MaterialGapAlert,
    Opportunity,
    WatchList,
)
from app.repositories.opportunity import MAIN_BREAKDOWN_CLASSIFICATIONS
from app.services.operations_service import OperationsService


class ExecutiveAgent:
    """Coordinates system signals into the actor's top priorities."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def top_priorities(self) -> list[dict]:
        now = datetime.now(timezone.utc)
        candidates: list[dict] = []
        candidates.extend(self._platform_check_in_priorities())
        candidates.extend(self._deadline_priorities(now))
        candidates.extend(self._strong_match_priorities())
        candidates.extend(self._career_task_priorities())
        candidates.extend(self._material_gap_priorities())
        candidates.extend(self._goal_priorities())
        candidates.extend(self._watch_list_priorities())
        candidates.extend(self._relationship_priorities())
        candidates.extend(self._calendar_priorities(now))
        candidates.extend(self._analytics_priorities())
        candidates.extend(self._career_memory_priorities())
        candidates.sort(key=lambda item: (item["urgency"], item["rank_hint"]), reverse=True)
        selected = candidates[:3]
        if not selected:
            selected = [
                {
                    "title": "Add your first casting goal",
                    "reason": "Casting goals help the system prioritize breakdowns, materials, and career tasks.",
                    "category": "Casting Goals",
                    "action_label": "Open Career",
                    "target_path": "/career",
                    "urgency": 35,
                    "rank_hint": 1,
                }
            ]
        return [
            {key: value for key, value in {**item, "rank": index + 1}.items() if key != "rank_hint"}
            for index, item in enumerate(selected)
        ]

    def _deadline_priorities(self, now: datetime) -> list[dict]:
        soon = now + timedelta(days=3)
        rows = []
        for item in self.db.scalars(
            select(Opportunity)
            .where(Opportunity.is_demo_data.is_(False))
            .where(Opportunity.visibility_status == "visible")
            .where(Opportunity.breakdown_classification.in_(MAIN_BREAKDOWN_CLASSIFICATIONS))
        ):
            deadline = item.submission_deadline or item.audition_deadline
            if not deadline:
                continue
            deadline = deadline if deadline.tzinfo else deadline.replace(tzinfo=timezone.utc)
            if deadline > soon:
                continue
            hours = max(0, int((deadline - now).total_seconds() // 3600))
            rows.append(
                {
                    "title": f"Submit to {item.role} before deadline",
                    "reason": f"{item.project} is due in about {hours} hours and is currently visible in Breakdowns.",
                    "category": "Breakdown Deadline",
                    "action_label": "Open Breakdowns",
                    "target_path": "/breakdowns",
                    "urgency": 100 - min(hours, 72),
                    "rank_hint": item.quality_score,
                }
            )
        return rows

    def _platform_check_in_priorities(self) -> list[dict]:
        check_ins = OperationsService(self.db).today_platform_check_ins()
        unchecked = [item for item in check_ins if not item["checked_today"]]
        if not unchecked:
            return []
        if len(unchecked) == 1:
            title = f"Check {unchecked[0]['platform_name']}"
            reason = f"{unchecked[0]['platform_name']} has not been checked today."
        else:
            names = ", ".join(str(item["platform_name"]) for item in unchecked[:3])
            title = f"Check casting platforms: {names}"
            reason = f"{len(unchecked)} subscribed casting platform(s) have not been checked today."
        return [
            {
                "title": title,
                "reason": reason,
                "category": "Platform Check-In",
                "action_label": "Open Dashboard",
                "target_path": "/",
                "urgency": 82,
                "rank_hint": len(unchecked),
            }
        ]

    def _strong_match_priorities(self) -> list[dict]:
        rows = []
        recommendations = self.db.scalars(
            select(AgentRecommendation)
            .where(AgentRecommendation.match_type == "Strong Match")
            .order_by(AgentRecommendation.score.desc(), AgentRecommendation.created_at.desc())
            .limit(3)
        )
        for recommendation in recommendations:
            opportunity = self.db.get(Opportunity, recommendation.opportunity_id)
            if not opportunity or opportunity.is_demo_data or opportunity.visibility_status != "visible":
                continue
            rows.append(
                {
                    "title": f"Review strong match: {opportunity.role}",
                    "reason": f"The strategy score is {recommendation.score}, so this is worth reviewing before lower-fit work.",
                    "category": "Recommended Strategy",
                    "action_label": "Open Breakdowns",
                    "target_path": "/breakdowns",
                    "urgency": min(95, 55 + recommendation.score // 2),
                    "rank_hint": recommendation.score,
                }
            )
        return rows

    def _career_task_priorities(self) -> list[dict]:
        rows = []
        for task in self.db.scalars(
            select(CareerDevelopmentTask)
            .where(CareerDevelopmentTask.status != "Completed")
            .order_by(CareerDevelopmentTask.priority.desc(), CareerDevelopmentTask.created_at.desc())
            .limit(4)
        ):
            impact_bonus = 15 if task.estimated_impact == "High" else 5
            priority_bonus = {"High": 25, "Medium": 15, "Low": 5}.get(task.priority, 10)
            rows.append(
                {
                    "title": task.title,
                    "reason": task.reason or task.description or "This open career task supports future recommendations.",
                    "category": "Career Task",
                    "action_label": "Open Career",
                    "target_path": "/career",
                    "urgency": 40 + impact_bonus + priority_bonus,
                    "rank_hint": priority_bonus,
                }
            )
        return rows

    def _material_gap_priorities(self) -> list[dict]:
        rows = []
        for gap in self.db.scalars(
            select(MaterialGapAlert)
            .where(MaterialGapAlert.status == "Open")
            .order_by(MaterialGapAlert.priority.desc(), MaterialGapAlert.created_at.desc())
            .limit(3)
        ):
            rows.append(
                {
                    "title": gap.recommended_action,
                    "reason": gap.message,
                    "category": "Material Gap",
                    "action_label": "Open Materials",
                    "target_path": "/materials",
                    "urgency": 70 if gap.priority == "High" else 55,
                    "rank_hint": 10,
                }
            )
        return rows

    def _goal_priorities(self) -> list[dict]:
        goals = list(
            self.db.scalars(
                select(CastingGoal)
                .where(CastingGoal.status == "Active")
                .order_by(CastingGoal.priority.desc(), CastingGoal.updated_at.desc())
                .limit(2)
            )
        )
        return [
            {
                "title": f"Advance casting goal: {goal.title}",
                "reason": goal.notes or "Active casting goals should guide today's submissions and material choices.",
                "category": "Casting Goal",
                "action_label": "Open Career",
                "target_path": "/career",
                "urgency": 58 if goal.priority == "High" else 45,
                "rank_hint": 8,
            }
            for goal in goals
        ]

    def _watch_list_priorities(self) -> list[dict]:
        watch_lists = list(
            self.db.scalars(
                select(WatchList)
                .where(WatchList.enabled.is_(True), WatchList.match_count > 0)
                .order_by(WatchList.priority.desc(), WatchList.last_matched_at.desc().nullslast())
                .limit(2)
            )
        )
        return [
            {
                "title": f"Review Watch List matches: {item.title}",
                "reason": f"{item.match_count} tracked breakdown signal(s) matched this Watch List.",
                "category": "Watch List",
                "action_label": "Open Breakdowns",
                "target_path": "/breakdowns",
                "urgency": 62 if item.priority == "High" else 48,
                "rank_hint": item.match_count,
            }
            for item in watch_lists
        ]

    def _relationship_priorities(self) -> list[dict]:
        rows = []
        cutoff = (datetime.now(timezone.utc) - timedelta(days=60)).date()
        for relationship in self.db.scalars(select(ActorRelationship).limit(4)):
            last = relationship.last_contact_date
            if last and last > cutoff:
                continue
            rows.append(
                {
                    "title": f"Refresh relationship notes for {relationship.name}",
                    "reason": f"{relationship.role_title} relationship is marked {relationship.relationship_strength}; update notes or next follow-up.",
                    "category": "Relationship",
                    "action_label": "Open Relationships",
                    "target_path": "/relationships",
                    "urgency": 42,
                    "rank_hint": 4,
                }
            )
        return rows

    def _calendar_priorities(self, now: datetime) -> list[dict]:
        soon = now + timedelta(days=2)
        rows = []
        for event in self.db.scalars(
            select(AuditionCalendarEvent)
            .where(AuditionCalendarEvent.start_datetime >= now, AuditionCalendarEvent.start_datetime <= soon)
            .order_by(AuditionCalendarEvent.start_datetime.asc())
            .limit(3)
        ):
            rows.append(
                {
                    "title": event.title,
                    "reason": f"{event.event_type} is coming up on {event.start_datetime:%b} {event.start_datetime.day}.",
                    "category": "Calendar",
                    "action_label": "Open Calendar",
                    "target_path": "/calendar",
                    "urgency": 65,
                    "rank_hint": 6,
                }
            )
        return rows

    def _analytics_priorities(self) -> list[dict]:
        insight = self.db.scalars(
            select(LearningInsight).order_by(LearningInsight.created_at.desc()).limit(1)
        ).first()
        if not insight:
            return []
        archetypes = (insight.trends or {}).get("highest_performing_archetypes") or []
        if not archetypes:
            return []
        label = ", ".join(archetypes[:3])
        return [
            {
                "title": f"Lean into what is working: {label}",
                "reason": insight.explanation,
                "category": "Analytics",
                "action_label": "Open Analytics",
                "target_path": "/analytics",
                "urgency": 60,
                "rank_hint": len(archetypes),
            }
        ]

    def _career_memory_priorities(self) -> list[dict]:
        memory = self.db.scalars(select(CareerMemory).order_by(CareerMemory.updated_at.desc()).limit(1)).first()
        if not memory:
            return []
        rows = []
        if memory.current_focus:
            rows.append(
                {
                    "title": f"Stay aligned with focus: {memory.current_focus}",
                    "reason": memory.executive_notes or memory.career_notes or "Career Memory is guiding today's prioritization.",
                    "category": "Career Memory",
                    "action_label": "Open Career",
                    "target_path": "/career",
                    "urgency": 57,
                    "rank_hint": 5,
                }
            )
        if memory.stretch_archetypes:
            rows.append(
                {
                    "title": f"Build stretch lane: {', '.join(memory.stretch_archetypes[:2])}",
                    "reason": "These stretch archetypes are saved in Career Memory and should influence materials and breakdown review.",
                    "category": "Career Memory",
                    "action_label": "Open Career",
                    "target_path": "/career",
                    "urgency": 52,
                    "rank_hint": len(memory.stretch_archetypes),
                }
            )
        return rows
