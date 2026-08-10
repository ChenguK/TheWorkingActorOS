from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.core.config import Settings
from app.db.models import (
    ActorProfile,
    AgentRecommendation,
    LearningInsight,
    Opportunity,
    RecommendationFeedback,
)
from app.services.command_center_service import CommandCenterService
from app.services.opportunity_intelligence_service import OpportunityIntelligenceService
from app.services.portfolio_seed_ownership_service import PORTFOLIO_PROFILE_ID
from app.services.sanitized_portfolio_manifest import (
    AGENT_RECOMMENDATION_ID,
    OPPORTUNITY_IDS,
    RECOMMENDATION_FEEDBACK_ID,
    build_sanitized_portfolio_manifest,
)
from app.services.sanitized_portfolio_recommendation_service import (
    PORTFOLIO_FEEDBACK_COLLISION_ERROR,
    PORTFOLIO_RECOMMENDATION_COLLISION_ERROR,
    SanitizedPortfolioRecommendationService,
)
from scripts.seed_sanitized_portfolio import run


pytestmark = pytest.mark.contract_smoke
AS_OF_A = datetime(2035, 4, 8, 16, 0, tzinfo=timezone.utc)
AS_OF_B = AS_OF_A + timedelta(days=60)


def settings() -> Settings:
    return Settings(
        _env_file=None,
        environment="development",
        sanitized_portfolio_seed_enabled=True,
    )


def test_recommendation_feedback_is_durable_idempotent_stable_and_scored(db) -> None:
    from app.core.database import SessionLocal

    db.close()
    run(execute=True, reset=False, settings=settings(), session_factory=SessionLocal, as_of=AS_OF_A)
    with SessionLocal() as fresh:
        recommendation = fresh.get(AgentRecommendation, AGENT_RECOMMENDATION_ID)
        feedback = fresh.get(RecommendationFeedback, RECOMMENDATION_FEEDBACK_ID)
        assert recommendation is not None and feedback is not None
        assert recommendation.actor_profile_id == PORTFOLIO_PROFILE_ID
        assert recommendation.opportunity_id == OPPORTUNITY_IDS[0]
        assert recommendation.score == 91
        assert feedback.actor_profile_id == PORTFOLIO_PROFILE_ID
        assert feedback.opportunity_id == OPPORTUNITY_IDS[0]
        assert feedback.recommendation_id == recommendation.id
        assert feedback.created_at == AS_OF_A - timedelta(hours=6)
        assert fresh.scalar(select(func.count()).select_from(AgentRecommendation)) == 1
        assert fresh.scalar(select(func.count()).select_from(RecommendationFeedback)) == 1
        assert fresh.scalar(select(func.count()).select_from(LearningInsight)) == 0

        actor = fresh.get(ActorProfile, PORTFOLIO_PROFILE_ID)
        candidates = CommandCenterService(fresh).read_opportunity_candidates()
        contexts = CommandCenterService(fresh)._read_scoring_contexts(candidates, actor)
        positive = OpportunityIntelligenceService(fresh).score(
            fresh.get(Opportunity, OPPORTUNITY_IDS[0]),
            actor,
            contexts[OPPORTUNITY_IDS[0]],
            as_of=AS_OF_A,
        )
        neutral = OpportunityIntelligenceService(fresh).score(
            fresh.get(Opportunity, OPPORTUNITY_IDS[1]),
            actor,
            contexts[OPPORTUNITY_IDS[1]],
            as_of=AS_OF_A,
        )
        positive_factors = [
            factor for category in positive.categories for factor in category.factors
        ]
        neutral_factors = [factor for category in neutral.categories for factor in category.factors]
        assert any(factor.id == "interest.feedback.fits_me" for factor in positive_factors)
        assert not any(factor.id.startswith("interest.feedback.") for factor in neutral_factors)

    run(execute=True, reset=False, settings=settings(), session_factory=SessionLocal, as_of=AS_OF_B)
    with SessionLocal() as fresh:
        assert fresh.scalar(select(func.count()).select_from(AgentRecommendation)) == 1
        assert fresh.scalar(select(func.count()).select_from(RecommendationFeedback)) == 1
        assert fresh.get(RecommendationFeedback, RECOMMENDATION_FEEDBACK_ID).created_at == (
            AS_OF_A - timedelta(hours=6)
        )


def test_owned_update_and_scoped_reset_preserve_unrelated_records(db) -> None:
    from app.core.database import SessionLocal

    db.close()
    run(execute=True, reset=False, settings=settings(), session_factory=SessionLocal, as_of=AS_OF_A)
    with SessionLocal() as fresh:
        ordinary_actor = ActorProfile(
            name="Unrelated Fictional Performer",
            sag_status="Unknown",
            union_status="Unknown",
            current_location="Chicago, IL",
            playable_age_min=30,
            playable_age_max=40,
        )
        ordinary_opportunity = Opportunity(
            role="Unrelated Role",
            project="Unrelated Project",
            union="Non-Union",
            location="Chicago, IL",
            description="An unrelated casting record.",
        )
        fresh.add_all([ordinary_actor, ordinary_opportunity])
        fresh.flush()
        owned = fresh.get(AgentRecommendation, AGENT_RECOMMENDATION_ID)
        ordinary_recommendation = AgentRecommendation(
            actor_profile_id=ordinary_actor.id,
            opportunity_id=ordinary_opportunity.id,
            **{
                column: getattr(owned, column)
                for column in SanitizedPortfolioRecommendationService._recommendation_fields(
                    build_sanitized_portfolio_manifest(AS_OF_A)
                )
                if column not in {"actor_profile_id", "opportunity_id"}
            },
        )
        fresh.add(ordinary_recommendation)
        fresh.flush()
        ordinary_feedback = RecommendationFeedback(
            actor_profile_id=ordinary_actor.id,
            opportunity_id=ordinary_opportunity.id,
            recommendation_id=ordinary_recommendation.id,
            feedback_type="This Fits Me",
            fit_reasons=["Unrelated reason"],
        )
        fresh.add(ordinary_feedback)
        fresh.commit()
        ordinary_ids = (ordinary_recommendation.id, ordinary_feedback.id)

        manifest = build_sanitized_portfolio_manifest(AS_OF_B)
        changed = replace(
            manifest,
            recommendation=replace(manifest.recommendation, match_type="Portfolio Highlight"),
            feedback=replace(manifest.feedback, fit_reasons=("Updated fictional fit",)),
        )
        service = SanitizedPortfolioRecommendationService(fresh)
        plan = service.plan(changed)
        assert (plan.recommendation_action, plan.feedback_action) == ("update", "update")
        service.apply(plan)
        fresh.commit()
        assert fresh.get(AgentRecommendation, AGENT_RECOMMENDATION_ID).match_type == (
            "Portfolio Highlight"
        )
        assert fresh.get(RecommendationFeedback, RECOMMENDATION_FEEDBACK_ID).fit_reasons == [
            "Updated fictional fit"
        ]
        assert fresh.get(RecommendationFeedback, RECOMMENDATION_FEEDBACK_ID).created_at == (
            AS_OF_A - timedelta(hours=6)
        )

        service.reset(changed)
        fresh.commit()

    with SessionLocal() as fresh:
        assert fresh.get(AgentRecommendation, AGENT_RECOMMENDATION_ID) is None
        assert fresh.get(RecommendationFeedback, RECOMMENDATION_FEEDBACK_ID) is None
        assert fresh.get(AgentRecommendation, ordinary_ids[0]) is not None
        assert fresh.get(RecommendationFeedback, ordinary_ids[1]) is not None
        assert fresh.scalar(select(func.count()).select_from(Opportunity)) == 8


def test_feedback_failure_rolls_back_the_complete_seed(db, monkeypatch) -> None:
    from app.core.database import SessionLocal

    db.close()
    original_add = SessionLocal.class_.add

    def fail_feedback(self, instance, *args, **kwargs):
        if isinstance(instance, RecommendationFeedback):
            raise RuntimeError("forced RecommendationFeedback failure")
        return original_add(self, instance, *args, **kwargs)

    monkeypatch.setattr(SessionLocal.class_, "add", fail_feedback)
    with pytest.raises(RuntimeError, match="forced RecommendationFeedback failure"):
        run(
            execute=True,
            reset=False,
            settings=settings(),
            session_factory=SessionLocal,
            as_of=AS_OF_A,
        )

    with SessionLocal() as fresh:
        assert fresh.scalar(select(func.count()).select_from(AgentRecommendation)) == 0
        assert fresh.scalar(select(func.count()).select_from(RecommendationFeedback)) == 0
        assert fresh.scalar(select(func.count()).select_from(Opportunity)) == 0


def test_reserved_identity_collisions_fail_closed(db) -> None:
    from app.core.database import SessionLocal

    db.close()
    run(execute=True, reset=False, settings=settings(), session_factory=SessionLocal, as_of=AS_OF_A)
    manifest = build_sanitized_portfolio_manifest(AS_OF_A)
    with SessionLocal() as fresh:
        recommendation = fresh.get(AgentRecommendation, AGENT_RECOMMENDATION_ID)
        recommendation.actor_profile_id = (
            fresh.scalar(select(ActorProfile.id).where(ActorProfile.id != PORTFOLIO_PROFILE_ID))
            or recommendation.actor_profile_id
        )
        # A distinct owner is required to prove the reserved recommendation ID cannot be adopted.
        other = ActorProfile(
            name="Collision Actor",
            sag_status="Unknown",
            union_status="Unknown",
            current_location="Chicago, IL",
            playable_age_min=30,
            playable_age_max=40,
        )
        fresh.add(other)
        fresh.flush()
        recommendation.actor_profile_id = other.id
        fresh.flush()
        with pytest.raises(ValueError, match=PORTFOLIO_RECOMMENDATION_COLLISION_ERROR):
            SanitizedPortfolioRecommendationService(fresh).plan(manifest)
        fresh.rollback()

    with SessionLocal() as fresh:
        feedback = fresh.get(RecommendationFeedback, RECOMMENDATION_FEEDBACK_ID)
        feedback.recommendation_id = None
        fresh.flush()
        with pytest.raises(ValueError, match=PORTFOLIO_FEEDBACK_COLLISION_ERROR):
            SanitizedPortfolioRecommendationService(fresh).plan(manifest)
        fresh.rollback()
