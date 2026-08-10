from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from app.db.models import (
    ActorProfile,
    AgentRecommendation,
    Opportunity,
    RecommendationFeedback,
)
from app.services.portfolio_seed_ownership_service import (
    PORTFOLIO_PROFILE_ID,
    PORTFOLIO_PROFILE_NAME,
    PortfolioSeedOwnershipService,
)
from app.services.sanitized_portfolio_manifest import SanitizedPortfolioManifest


RecommendationSeedAction = Literal["create", "update", "unchanged"]
PORTFOLIO_RECOMMENDATION_COLLISION_ERROR = (
    "reserved sanitized portfolio recommendation identity is already in use"
)
PORTFOLIO_FEEDBACK_COLLISION_ERROR = (
    "reserved sanitized portfolio feedback identity is already in use"
)


@dataclass(frozen=True)
class RecommendationSeedPlan:
    manifest: SanitizedPortfolioManifest
    recommendation_action: RecommendationSeedAction
    feedback_action: RecommendationSeedAction


class SanitizedPortfolioRecommendationService:
    """Reconciles the bounded recommendation graph without committing or learning."""

    def __init__(self, db: Session):
        self.db = db

    def plan(
        self,
        manifest: SanitizedPortfolioManifest,
        *,
        allow_planned_actor_create: bool = False,
        allow_planned_opportunity_create: bool = False,
    ) -> RecommendationSeedPlan:
        actor = self.db.get(ActorProfile, PORTFOLIO_PROFILE_ID)
        if actor is None:
            if not allow_planned_actor_create:
                raise ValueError(PORTFOLIO_RECOMMENDATION_COLLISION_ERROR)
        elif actor.name != PORTFOLIO_PROFILE_NAME:
            raise ValueError(PORTFOLIO_RECOMMENDATION_COLLISION_ERROR)

        definition = manifest.recommendation
        opportunity = self.db.get(Opportunity, definition.opportunity_id)
        if opportunity is None:
            if not allow_planned_opportunity_create:
                raise ValueError(PORTFOLIO_RECOMMENDATION_COLLISION_ERROR)
        elif not PortfolioSeedOwnershipService.is_portfolio_owned(opportunity):
            raise ValueError(PORTFOLIO_RECOMMENDATION_COLLISION_ERROR)

        recommendation = self.db.get(AgentRecommendation, definition.id)
        if recommendation is not None and not self._recommendation_owned(
            recommendation, definition.opportunity_id
        ):
            raise ValueError(PORTFOLIO_RECOMMENDATION_COLLISION_ERROR)
        recommendation_fields = self._recommendation_fields(manifest)
        recommendation_action = self._action(recommendation, recommendation_fields)

        feedback_definition = manifest.feedback
        feedback = self.db.get(RecommendationFeedback, feedback_definition.id)
        if feedback is not None and not self._feedback_owned(
            feedback,
            feedback_definition.opportunity_id,
            feedback_definition.recommendation_id,
        ):
            raise ValueError(PORTFOLIO_FEEDBACK_COLLISION_ERROR)
        feedback_fields = self._feedback_fields(manifest)
        feedback_action = self._action(feedback, feedback_fields)
        return RecommendationSeedPlan(
            manifest,
            recommendation_action,
            feedback_action,
        )

    def apply(self, plan: RecommendationSeedPlan) -> None:
        recommendation_definition = plan.manifest.recommendation
        recommendation = self.db.get(AgentRecommendation, recommendation_definition.id)
        recommendation_fields = self._recommendation_fields(plan.manifest)
        if plan.recommendation_action == "create":
            recommendation = AgentRecommendation(
                id=recommendation_definition.id,
                **recommendation_fields,
            )
            self.db.add(recommendation)
            self.db.flush()
        elif plan.recommendation_action == "update":
            for name, value in recommendation_fields.items():
                setattr(recommendation, name, value)

        feedback_definition = plan.manifest.feedback
        feedback = self.db.get(RecommendationFeedback, feedback_definition.id)
        feedback_fields = self._feedback_fields(plan.manifest)
        if plan.feedback_action == "create":
            self.db.add(
                RecommendationFeedback(
                    id=feedback_definition.id,
                    created_at=feedback_definition.created_at,
                    **feedback_fields,
                )
            )
        elif plan.feedback_action == "update":
            for name, value in feedback_fields.items():
                setattr(feedback, name, value)

    def reset(self, manifest: SanitizedPortfolioManifest) -> None:
        feedback = self.db.get(RecommendationFeedback, manifest.feedback.id)
        if feedback is not None:
            if not self._feedback_owned(
                feedback,
                manifest.feedback.opportunity_id,
                manifest.feedback.recommendation_id,
            ):
                raise ValueError(PORTFOLIO_FEEDBACK_COLLISION_ERROR)
            self.db.delete(feedback)
        recommendation = self.db.get(AgentRecommendation, manifest.recommendation.id)
        if recommendation is not None:
            if not self._recommendation_owned(
                recommendation, manifest.recommendation.opportunity_id
            ):
                raise ValueError(PORTFOLIO_RECOMMENDATION_COLLISION_ERROR)
            self.db.delete(recommendation)
        self.db.flush()

    @staticmethod
    def _action(record, fields: dict) -> RecommendationSeedAction:
        if record is None:
            return "create"
        return (
            "unchanged"
            if all(getattr(record, name) == value for name, value in fields.items())
            else "update"
        )

    @staticmethod
    def _recommendation_owned(recommendation: AgentRecommendation, opportunity_id) -> bool:
        return (
            recommendation.actor_profile_id == PORTFOLIO_PROFILE_ID
            and recommendation.opportunity_id == opportunity_id
        )

    @staticmethod
    def _feedback_owned(feedback, opportunity_id, recommendation_id) -> bool:
        return (
            feedback.actor_profile_id == PORTFOLIO_PROFILE_ID
            and feedback.opportunity_id == opportunity_id
            and feedback.recommendation_id == recommendation_id
        )

    @staticmethod
    def _recommendation_fields(manifest: SanitizedPortfolioManifest) -> dict:
        item = manifest.recommendation
        return {
            "actor_profile_id": PORTFOLIO_PROFILE_ID,
            "opportunity_id": item.opportunity_id,
            "agent_version": item.agent_version,
            "score": item.score,
            "match_type": item.match_type,
            "display_opportunity": item.display_opportunity,
            "explanation": item.explanation,
            "score_breakdown": dict(item.score_breakdown),
            "audition_type": item.audition_type,
            "audition_decision": item.audition_decision,
            "audition_explanation": item.audition_explanation,
            "travel_explanation": item.travel_explanation,
            "archetype_explanation": item.archetype_explanation,
            "asset_explanation": item.asset_explanation,
            "submission_strategy_explanation": item.submission_strategy_explanation,
            "confidence_level": item.confidence_level,
            "risk_level": item.risk_level,
            "risk_explanation": item.risk_explanation,
            "recommended_note": item.recommended_note,
        }

    @staticmethod
    def _feedback_fields(manifest: SanitizedPortfolioManifest) -> dict:
        item = manifest.feedback
        return {
            "actor_profile_id": PORTFOLIO_PROFILE_ID,
            "opportunity_id": item.opportunity_id,
            "recommendation_id": item.recommendation_id,
            "feedback_type": item.feedback_type,
            "fit_reasons": list(item.fit_reasons),
            "notes": None,
        }
