from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

from app.core.config import Settings
from app.db.models import (
    ActorProfile,
    AgentRecommendation,
    Asset,
    AuditionCalendarEvent,
    AuditionJournalEntry,
    CareerMemory,
    CastingGoal,
    LearningInsight,
    Opportunity,
    RecommendationFeedback,
    Submission,
    WatchList,
)
from app.services.portfolio_seed_ownership_service import PORTFOLIO_PROFILE_ID
from app.services.executive_intelligence_service import ExecutiveIntelligenceService
from app.services.sanitized_portfolio_career_targeting_service import (
    SanitizedPortfolioCareerTargetingService,
)
from app.services.sanitized_portfolio_manifest import (
    CAREER_MEMORY_ID,
    CASTING_GOAL_ID,
    build_sanitized_portfolio_manifest,
)
from scripts.seed_sanitized_portfolio import run


pytestmark = pytest.mark.contract_smoke
AS_OF = datetime(2033, 5, 4, 12, 0, tzinfo=timezone.utc)


def settings() -> Settings:
    return Settings(
        _env_file=None,
        environment="development",
        sanitized_portfolio_seed_enabled=True,
    )


def test_career_targeting_is_durable_idempotent_isolated_and_scoped_reset(db) -> None:
    from app.core.database import SessionLocal

    other = ActorProfile(
        name="Ordinary Actor",
        sag_status="Unknown",
        union_status="Unknown",
        current_location="Chicago, IL",
        playable_age_min=25,
        playable_age_max=45,
    )
    db.add(other)
    db.flush()
    conflicting_watch = WatchList(
        actor_profile_id=other.id,
        title="Casting Goal: Build a Film and Television Guest-Star Track",
        category="Other actor",
        terms=["untouched"],
        priority="Low",
        enabled=True,
    )
    null_watch = WatchList(
        actor_profile_id=None,
        title="Casting Goal: Build a Film and Television Guest-Star Track",
        category="Ownerless",
        terms=["untouched"],
        priority="Low",
        enabled=True,
    )
    other_memory = CareerMemory(actor_profile_id=other.id, current_focus="Untouched")
    null_memory = CareerMemory(actor_profile_id=None, current_focus="Ownerless")
    ordinary_opportunity = Opportunity(
        role="Unrelated Performer",
        project="Unrelated Project",
        union="Non-Union",
        location="Chicago, IL",
        description="An unrelated casting record with no targeting terms.",
        is_demo_data=False,
    )
    db.add_all([conflicting_watch, null_watch, other_memory, null_memory, ordinary_opportunity])
    db.commit()
    ids = (conflicting_watch.id, null_watch.id, other_memory.id, null_memory.id)
    ordinary_opportunity_id = ordinary_opportunity.id
    db.close()

    run(execute=True, reset=False, settings=settings(), session_factory=SessionLocal, as_of=AS_OF)
    run(execute=True, reset=False, settings=settings(), session_factory=SessionLocal, as_of=AS_OF)

    with SessionLocal() as fresh:
        goal = fresh.get(CastingGoal, CASTING_GOAL_ID)
        memory = fresh.get(CareerMemory, CAREER_MEMORY_ID)
        watches = list(
            fresh.scalars(
                select(WatchList).where(WatchList.actor_profile_id == PORTFOLIO_PROFILE_ID)
            )
        )
        assert goal is not None and goal.actor_profile_id == PORTFOLIO_PROFILE_ID
        assert goal.status == "Active" and goal.priority == "High"
        assert memory is not None and memory.actor_profile_id == PORTFOLIO_PROFILE_ID
        assert len(watches) == 1
        assert watches[0].category == "Casting Goals"
        assert fresh.get(WatchList, ids[0]).terms == ["untouched"]
        assert fresh.get(WatchList, ids[1]).actor_profile_id is None
        assert fresh.get(CareerMemory, ids[2]).current_focus == "Untouched"
        assert fresh.get(CareerMemory, ids[3]).actor_profile_id is None
        assert fresh.scalar(select(func.count()).select_from(Opportunity)) == 8
        ordinary_reloaded = fresh.get(Opportunity, ordinary_opportunity_id)
        assert ordinary_reloaded.watchlist_match_names == []
        assert ordinary_reloaded.watchlist_match_count == 0
        assert ordinary_reloaded.watchlist_notification is None
        portfolio_opportunities = list(
            fresh.scalars(select(Opportunity).where(Opportunity.id != ordinary_opportunity_id))
        )
        assert any(item.watchlist_match_count > 0 for item in portfolio_opportunities)
        assert fresh.scalar(select(func.count()).select_from(Submission)) == 3
        assert fresh.scalar(select(func.count()).select_from(AuditionCalendarEvent)) == 10
        assert fresh.scalar(select(func.count()).select_from(AuditionJournalEntry)) == 3
        for model in (
            AgentRecommendation,
            RecommendationFeedback,
            Asset,
            LearningInsight,
        ):
            assert fresh.scalar(select(func.count()).select_from(model)) == 0

        manifest = build_sanitized_portfolio_manifest(AS_OF)
        SanitizedPortfolioCareerTargetingService(fresh).reset(manifest)
        fresh.commit()

    with SessionLocal() as fresh:
        assert fresh.get(CastingGoal, CASTING_GOAL_ID) is None
        assert fresh.get(CareerMemory, CAREER_MEMORY_ID) is None
        assert (
            fresh.scalar(
                select(func.count())
                .select_from(WatchList)
                .where(WatchList.actor_profile_id == PORTFOLIO_PROFILE_ID)
            )
            == 0
        )
        assert fresh.scalar(select(func.count()).select_from(Opportunity)) == 8
        assert fresh.get(ActorProfile, PORTFOLIO_PROFILE_ID) is not None
        assert all(
            fresh.get(type_, id_) is not None
            for type_, id_ in zip(
                (WatchList, WatchList, CareerMemory, CareerMemory), ids, strict=True
            )
        )


def test_career_targeting_collision_rolls_back_current_seed_invocation(db) -> None:
    from app.core.database import SessionLocal

    other = ActorProfile(
        name="Collision Owner",
        sag_status="Unknown",
        union_status="Unknown",
        current_location="Chicago, IL",
        playable_age_min=25,
        playable_age_max=45,
    )
    db.add(other)
    db.flush()
    db.add(CareerMemory(id=CAREER_MEMORY_ID, actor_profile_id=other.id))
    db.commit()
    db.close()

    with pytest.raises(ValueError, match="CareerMemory identity is already in use"):
        run(
            execute=True,
            reset=False,
            settings=settings(),
            session_factory=SessionLocal,
            as_of=AS_OF,
        )

    with SessionLocal() as fresh:
        assert fresh.get(CastingGoal, CASTING_GOAL_ID) is None
        assert fresh.get(ActorProfile, PORTFOLIO_PROFILE_ID) is None
        assert fresh.scalar(select(func.count()).select_from(Opportunity)) == 0


def test_failure_after_watch_derivation_rolls_back_all_current_invocation(db, monkeypatch) -> None:
    from app.core.database import SessionLocal

    db.close()

    def fail_memory(*args, **kwargs):
        raise RuntimeError("forced CareerMemory failure")

    monkeypatch.setattr(
        ExecutiveIntelligenceService,
        "get_or_create_memory_without_commit",
        fail_memory,
    )
    with pytest.raises(RuntimeError, match="forced CareerMemory failure"):
        run(
            execute=True,
            reset=False,
            settings=settings(),
            session_factory=SessionLocal,
            as_of=AS_OF,
        )

    with SessionLocal() as fresh:
        assert fresh.get(CastingGoal, CASTING_GOAL_ID) is None
        assert fresh.get(CareerMemory, CAREER_MEMORY_ID) is None
        assert fresh.scalar(select(func.count()).select_from(WatchList)) == 0
        assert fresh.get(ActorProfile, PORTFOLIO_PROFILE_ID) is None
        assert fresh.scalar(select(func.count()).select_from(Opportunity)) == 0
