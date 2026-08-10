from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal, Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ActorProfile, CareerMemory, CastingGoal, WatchList
from app.services.executive_intelligence_service import ExecutiveIntelligenceService
from app.services.portfolio_seed_ownership_service import (
    PORTFOLIO_PROFILE_ID,
    PORTFOLIO_PROFILE_NAME,
)
from app.services.sanitized_portfolio_manifest import (
    CAREER_MEMORY_ID,
    CASTING_GOAL_ID,
    SanitizedPortfolioManifest,
)
from app.services.watch_list_service import WatchListService
from app.services.workflow_connector_service import WorkflowConnectorService


SeedAction = Literal["create", "update", "unchanged"]


@dataclass(frozen=True)
class CareerTargetingPlan:
    manifest: SanitizedPortfolioManifest
    casting_goal_action: SeedAction
    watch_list_action: SeedAction
    career_memory_action: SeedAction


class SanitizedPortfolioCareerTargetingService:
    """Reconciles career-targeting records without owning commit or rollback."""

    def __init__(self, db: Session):
        self.db = db

    def plan(
        self, manifest: SanitizedPortfolioManifest, *, allow_planned_actor_create: bool = False
    ) -> CareerTargetingPlan:
        actor = self.db.get(ActorProfile, PORTFOLIO_PROFILE_ID)
        if actor is None:
            if not allow_planned_actor_create:
                raise ValueError(
                    "sanitized portfolio ActorProfile must exist before career targeting"
                )
        elif actor.name != PORTFOLIO_PROFILE_NAME:
            raise ValueError("sanitized portfolio ActorProfile must exist before career targeting")
        goal = self.db.get(CastingGoal, CASTING_GOAL_ID)
        if goal and goal.actor_profile_id != PORTFOLIO_PROFILE_ID:
            raise ValueError("reserved sanitized portfolio CastingGoal identity is already in use")
        memory = self.db.get(CareerMemory, CAREER_MEMORY_ID)
        if memory and memory.actor_profile_id != PORTFOLIO_PROFILE_ID:
            raise ValueError("reserved sanitized portfolio CareerMemory identity is already in use")
        watch = self.db.scalars(
            select(WatchList).where(
                WatchList.actor_profile_id == PORTFOLIO_PROFILE_ID,
                WatchList.title == self._watch_title(manifest),
            )
        ).first()
        return CareerTargetingPlan(
            manifest=manifest,
            casting_goal_action=self._action(goal, self._goal_fields(manifest)),
            watch_list_action=self._action(watch, self._watch_fields(manifest)),
            career_memory_action=self._action(memory, self._memory_fields(manifest)),
        )

    def apply(
        self, plan: CareerTargetingPlan, *, actor_created_in_transaction: bool = False
    ) -> None:
        if actor_created_in_transaction:
            actor = ActorProfile(id=PORTFOLIO_PROFILE_ID, name=PORTFOLIO_PROFILE_NAME)
        else:
            actor = self._require_actor()
        goal = self.db.get(CastingGoal, CASTING_GOAL_ID)
        goal_fields = self._goal_fields(plan.manifest)
        if goal is None:
            goal = CastingGoal(id=CASTING_GOAL_ID, **deepcopy(goal_fields))
            self.db.add(goal)
        elif goal.actor_profile_id != PORTFOLIO_PROFILE_ID:
            raise ValueError("reserved sanitized portfolio CastingGoal identity is already in use")
        else:
            if goal.title != goal_fields["title"]:
                previous = self.db.scalars(
                    select(WatchList).where(
                        WatchList.actor_profile_id == PORTFOLIO_PROFILE_ID,
                        WatchList.title == f"Casting Goal: {goal.title}",
                    )
                ).first()
                if previous:
                    self.db.delete(previous)
            self._update(goal, goal_fields)
        WorkflowConnectorService(self.db).after_casting_goal_saved(goal)
        self.db.flush()
        WatchListService(self.db).refresh_all()

        existing = self.db.get(CareerMemory, CAREER_MEMORY_ID)
        if existing and existing.actor_profile_id != PORTFOLIO_PROFILE_ID:
            raise ValueError("reserved sanitized portfolio CareerMemory identity is already in use")
        memory, _ = ExecutiveIntelligenceService(self.db).get_or_create_memory_without_commit(
            actor, memory_id=CAREER_MEMORY_ID
        )
        self._update(memory, self._memory_fields(plan.manifest))

    def reset(self, manifest: SanitizedPortfolioManifest) -> None:
        watch = self.db.scalars(
            select(WatchList).where(
                WatchList.actor_profile_id == PORTFOLIO_PROFILE_ID,
                WatchList.title == self._watch_title(manifest),
            )
        ).first()
        if watch:
            self.db.delete(watch)
        goal = self.db.get(CastingGoal, CASTING_GOAL_ID)
        if goal:
            if goal.actor_profile_id != PORTFOLIO_PROFILE_ID:
                raise ValueError(
                    "reserved sanitized portfolio CastingGoal identity is already in use"
                )
            self.db.delete(goal)
        memory = self.db.get(CareerMemory, CAREER_MEMORY_ID)
        if memory:
            if memory.actor_profile_id != PORTFOLIO_PROFILE_ID:
                raise ValueError(
                    "reserved sanitized portfolio CareerMemory identity is already in use"
                )
            self.db.delete(memory)

    def _require_actor(self) -> ActorProfile:
        actor = self.db.get(ActorProfile, PORTFOLIO_PROFILE_ID)
        if actor is None or actor.name != PORTFOLIO_PROFILE_NAME:
            raise ValueError("sanitized portfolio ActorProfile must exist before career targeting")
        return actor

    @staticmethod
    def _goal_fields(manifest: SanitizedPortfolioManifest) -> dict[str, Any]:
        goal = manifest.casting_goal
        return {
            "actor_profile_id": PORTFOLIO_PROFILE_ID,
            "title": goal.title,
            "goal_type": goal.goal_type,
            "target_archetypes": list(goal.target_archetypes),
            "target_role_types": list(goal.target_role_types),
            "target_project_types": list(goal.target_project_types),
            "target_markets": list(goal.target_markets),
            "target_casting_offices": [],
            "target_deadline": None,
            "priority": goal.priority,
            "status": goal.status,
            "notes": None,
        }

    @classmethod
    def _watch_title(cls, manifest: SanitizedPortfolioManifest) -> str:
        return f"Casting Goal: {manifest.casting_goal.title}"

    @classmethod
    def _watch_fields(cls, manifest: SanitizedPortfolioManifest) -> dict[str, Any]:
        goal = manifest.casting_goal
        terms = [
            goal.title,
            goal.goal_type,
            *goal.target_archetypes,
            *goal.target_role_types,
            *goal.target_project_types,
            *goal.target_markets,
        ]
        return {
            "actor_profile_id": PORTFOLIO_PROFILE_ID,
            "title": cls._watch_title(manifest),
            "category": "Casting Goals",
            "terms": list(dict.fromkeys(terms)),
            "priority": goal.priority,
            "enabled": True,
            "notes": "Automatically suggested from an active Casting Goal.",
        }

    @staticmethod
    def _memory_fields(manifest: SanitizedPortfolioManifest) -> dict[str, Any]:
        memory = manifest.career_memory
        return {
            "actor_profile_id": PORTFOLIO_PROFILE_ID,
            "current_focus": memory.current_focus,
            "current_career_goals": list(memory.current_career_goals),
            "stretch_archetypes": list(memory.stretch_archetypes),
            "preferred_project_types": list(memory.preferred_project_types),
            "preferred_markets": list(memory.preferred_markets),
        }

    @staticmethod
    def _action(record: object | None, fields: Mapping[str, Any]) -> SeedAction:
        if record is None:
            return "create"
        return (
            "unchanged"
            if all(getattr(record, key) == value for key, value in fields.items())
            else "update"
        )

    @staticmethod
    def _update(record: object, fields: Mapping[str, Any]) -> None:
        for key, value in fields.items():
            setattr(record, key, deepcopy(value))
