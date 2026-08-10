from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Mapping
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    ActorJournalEntry,
    ActorProfile,
    AgentRecommendation,
    AuditionCalendarEvent,
    AuditionJournalEntry,
    CallbackEvent,
    Opportunity,
    RecommendationFeedback,
    Submission,
)
from app.services.portfolio_seed_ownership_service import (
    PORTFOLIO_PROFILE_ID,
    PORTFOLIO_PROFILE_NAME,
    PortfolioSeedOwnershipService,
)
from app.services.sanitized_portfolio_manifest import (
    OpportunityManifest,
    SanitizedPortfolioManifest,
    build_sanitized_portfolio_manifest,
)


OpportunitySeedAction = Literal["create", "update", "unchanged"]
TEMPORAL_OPPORTUNITY_FIELDS = (
    "submission_deadline",
    "audition_deadline",
    "callback_date",
    "shoot_start_date",
    "shoot_end_date",
)
NON_TEMPORAL_OPPORTUNITY_FIELDS = (
    "source_type",
    "role",
    "project",
    "description",
    "project_type",
    "role_type",
    "union",
    "location",
    "audition_type",
    "status",
    "breakdown_classification",
    "visibility_status",
    "manual_review_required",
    "confidence_level",
    "source_reliability_score",
    "source_metadata",
    "role_details",
    "production_details",
)
PORTFOLIO_OPPORTUNITY_COLLISION_ERROR = (
    "reserved sanitized portfolio Opportunity identity is already in use"
)
PORTFOLIO_OPPORTUNITY_RESET_DEPENDENCY_ERROR = (
    "portfolio Opportunity reset requires full dependency-aware reset"
)


@dataclass(frozen=True)
class OpportunitySeedItemPlan:
    id: UUID
    scenario: str
    action: OpportunitySeedAction


@dataclass(frozen=True)
class OpportunitySeedPlan:
    manifest: SanitizedPortfolioManifest
    items: tuple[OpportunitySeedItemPlan, ...]

    @property
    def create_count(self) -> int:
        return sum(item.action == "create" for item in self.items)

    @property
    def update_count(self) -> int:
        return sum(item.action == "update" for item in self.items)

    @property
    def unchanged_count(self) -> int:
        return sum(item.action == "unchanged" for item in self.items)


class SanitizedPortfolioOpportunityService:
    """Plans and applies only manifest-owned Opportunity fields without committing."""

    def __init__(self, db: Session):
        self.db = db

    def plan(
        self, *, as_of: datetime, allow_planned_profile_create: bool = False
    ) -> OpportunitySeedPlan:
        manifest = build_sanitized_portfolio_manifest(as_of)
        profile = self.db.get(ActorProfile, PORTFOLIO_PROFILE_ID)
        if profile is None:
            if not allow_planned_profile_create:
                raise ValueError("sanitized portfolio ActorProfile must exist before Opportunities")
        elif profile.name != PORTFOLIO_PROFILE_NAME:
            raise ValueError("reserved sanitized portfolio profile identity is already in use")
        existing = self._reserved_opportunities(manifest)
        items = []
        for definition in manifest.opportunities:
            record = existing.get(definition.id)
            if record is None:
                action: OpportunitySeedAction = "create"
            else:
                self._require_owned(record)
                action = (
                    "unchanged"
                    if self._matches(record, self._non_temporal_fields(definition))
                    else "update"
                )
            items.append(OpportunitySeedItemPlan(definition.id, definition.scenario, action))
        return OpportunitySeedPlan(manifest=manifest, items=tuple(items))

    def apply(
        self, plan: OpportunitySeedPlan, *, profile_created_in_transaction: bool = False
    ) -> None:
        if not profile_created_in_transaction:
            self._require_profile()
        existing = self._reserved_opportunities(plan.manifest)
        definitions = {item.id: item for item in plan.manifest.opportunities}
        for item in plan.items:
            definition = definitions[item.id]
            record = existing.get(item.id)
            if item.action == "create":
                if record is not None:
                    raise ValueError(PORTFOLIO_OPPORTUNITY_COLLISION_ERROR)
                fields = {
                    **self._non_temporal_fields(definition),
                    **self._temporal_fields(definition),
                }
                self.db.add(Opportunity(id=definition.id, **deepcopy(fields)))
            elif item.action == "update":
                if record is None:
                    raise ValueError(PORTFOLIO_OPPORTUNITY_COLLISION_ERROR)
                self._require_owned(record)
                self._update(record, self._non_temporal_fields(definition))

    def reset_owned_opportunities(self) -> tuple[UUID, ...]:
        owned = PortfolioSeedOwnershipService(self.db).find_owned_opportunities()
        ids = tuple(item.id for item in owned)
        self._require_no_dependencies(ids)
        for opportunity in owned:
            self.db.delete(opportunity)
        return ids

    def _require_profile(self) -> ActorProfile:
        profile = self.db.get(ActorProfile, PORTFOLIO_PROFILE_ID)
        if profile is None:
            raise ValueError("sanitized portfolio ActorProfile must exist before Opportunities")
        if profile.name != PORTFOLIO_PROFILE_NAME:
            raise ValueError("reserved sanitized portfolio profile identity is already in use")
        return profile

    def _reserved_opportunities(
        self, manifest: SanitizedPortfolioManifest
    ) -> dict[UUID, Opportunity]:
        ids = tuple(item.id for item in manifest.opportunities)
        records = self.db.scalars(select(Opportunity).where(Opportunity.id.in_(ids))).all()
        return {item.id: item for item in records}

    @staticmethod
    def _require_owned(opportunity: Opportunity) -> None:
        if not PortfolioSeedOwnershipService.is_portfolio_owned(opportunity):
            raise ValueError(PORTFOLIO_OPPORTUNITY_COLLISION_ERROR)

    @staticmethod
    def _non_temporal_fields(definition: OpportunityManifest) -> dict[str, Any]:
        travel_review = definition.scenario == "travel_review"
        confidence_review = definition.scenario == "lower_confidence_review"
        values = {
            "source_type": "Manual Entry",
            "role": definition.role,
            "project": definition.project,
            "description": definition.description,
            "project_type": definition.project_type,
            "role_type": definition.role_type,
            "union": definition.union,
            "location": definition.location,
            "audition_type": definition.audition_type,
            "status": "open",
            "breakdown_classification": "Acting Role",
            "visibility_status": (
                "travel_exception"
                if travel_review
                else "hidden"
                if confidence_review
                else "visible"
            ),
            "manual_review_required": confidence_review,
            "confidence_level": definition.confidence_level,
            "source_reliability_score": definition.source_reliability_score,
            "source_metadata": deepcopy(definition.source_metadata),
            "role_details": {
                "fit_status": definition.intended_fit,
                "language_behavior": definition.language_behavior,
            },
            "production_details": {
                "deadline_band": definition.deadline_band.value,
                "travel_behavior": definition.travel_behavior,
                "predicted_action": definition.predicted_action,
            },
        }
        if tuple(values) != NON_TEMPORAL_OPPORTUNITY_FIELDS:
            raise RuntimeError("sanitized portfolio Opportunity field allowlist drifted")
        return values

    @staticmethod
    def _temporal_fields(definition: OpportunityManifest) -> dict[str, Any]:
        return {name: getattr(definition, name) for name in TEMPORAL_OPPORTUNITY_FIELDS}

    @staticmethod
    def _matches(record: Opportunity, fields: Mapping[str, Any]) -> bool:
        for key, value in fields.items():
            current = getattr(record, key)
            if key == "source_metadata":
                continue
            if key in {"role_details", "production_details"}:
                if not isinstance(current, Mapping) or any(
                    current.get(nested_key) != nested_value
                    for nested_key, nested_value in value.items()
                ):
                    return False
            elif current != value:
                return False
        return True

    @staticmethod
    def _update(record: Opportunity, fields: Mapping[str, Any]) -> None:
        for key, value in fields.items():
            if key == "source_metadata":
                continue
            if key in {"role_details", "production_details"}:
                merged = dict(getattr(record, key) or {})
                merged.update(deepcopy(value))
                setattr(record, key, merged)
            else:
                setattr(record, key, deepcopy(value))

    def _require_no_dependencies(self, opportunity_ids: tuple[UUID, ...]) -> None:
        if not opportunity_ids:
            return
        checks = (
            (Submission, Submission.opportunity_id),
            (AuditionCalendarEvent, AuditionCalendarEvent.opportunity_id),
            (AuditionJournalEntry, AuditionJournalEntry.opportunity_id),
            (ActorJournalEntry, ActorJournalEntry.linked_breakdown_id),
            (RecommendationFeedback, RecommendationFeedback.opportunity_id),
            (AgentRecommendation, AgentRecommendation.opportunity_id),
            (CallbackEvent, CallbackEvent.opportunity_id),
        )
        for model, column in checks:
            if self.db.scalar(select(model.id).where(column.in_(opportunity_ids)).limit(1)):
                raise ValueError(PORTFOLIO_OPPORTUNITY_RESET_DEPENDENCY_ERROR)
