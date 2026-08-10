from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.core.config import Settings
from app.db.models import (
    ActorProfile,
    AgentRecommendation,
    Asset,
    AuditionCalendarEvent,
    AuditionJournalEntry,
    CastingGoal,
    CareerMemory,
    Opportunity,
    RecommendationFeedback,
    Submission,
    TravelPreference,
    WatchList,
)
from app.services.portfolio_seed_ownership_service import (
    PORTFOLIO_PROFILE_ID,
    PORTFOLIO_SEED_NAMESPACE,
)
from app.services.sanitized_portfolio_manifest import OPPORTUNITY_IDS
from scripts.seed_sanitized_portfolio import run


pytestmark = pytest.mark.contract_smoke
AS_OF_A = datetime(2031, 3, 4, 15, 0, tzinfo=timezone.utc)
AS_OF_B = AS_OF_A + timedelta(days=30)


def authorized_settings() -> Settings:
    return Settings(
        _env_file=None,
        environment="development",
        sanitized_portfolio_seed_enabled=True,
    )


def test_opportunity_seed_is_durable_stable_idempotent_and_resettable(db) -> None:
    from app.core.database import SessionLocal

    ordinary_profile = ActorProfile(
        name="Ordinary User Profile",
        sag_status="Unknown",
        union_status="Unknown",
        current_location="Chicago, IL",
        playable_age_min=30,
        playable_age_max=40,
    )
    ordinary = Opportunity(
        role="Forensic Analyst",
        project="Signal at Dawn",
        union="SAG-AFTRA",
        location="Atlanta, GA",
        description="An ordinary user-owned casting record.",
        source_metadata={"portfolio_seed": {"namespace": "unrelated"}},
        is_demo_data=True,
    )
    db.add_all([ordinary_profile, ordinary])
    db.commit()
    ordinary_id = ordinary.id
    db.close()

    run(
        execute=True,
        reset=False,
        settings=authorized_settings(),
        session_factory=SessionLocal,
        as_of=AS_OF_A,
    )
    with SessionLocal() as fresh:
        seeded = [fresh.get(Opportunity, item_id) for item_id in OPPORTUNITY_IDS]
        assert all(item is not None for item in seeded)
        initial_dates = {
            item.id: (
                item.submission_deadline,
                item.audition_deadline,
                item.callback_date,
                item.shoot_start_date,
                item.shoot_end_date,
            )
            for item in seeded
            if item is not None
        }
        assert seeded[0].submission_deadline == AS_OF_A + timedelta(hours=20)
        assert [item.visibility_status for item in seeded if item] == [
            "visible",
            "visible",
            "visible",
            "visible",
            "hidden",
            "travel_exception",
            "visible",
        ]
        assert all(
            item.source_metadata == {"portfolio_seed": {"namespace": PORTFOLIO_SEED_NAMESPACE}}
            and item.is_demo_data is False
            for item in seeded
            if item
        )
        assert fresh.get(Opportunity, ordinary_id).is_demo_data is True

    run(
        execute=True,
        reset=False,
        settings=authorized_settings(),
        session_factory=SessionLocal,
        as_of=AS_OF_B,
    )
    with SessionLocal() as fresh:
        assert {
            item_id: (
                fresh.get(Opportunity, item_id).submission_deadline,
                fresh.get(Opportunity, item_id).audition_deadline,
                fresh.get(Opportunity, item_id).callback_date,
                fresh.get(Opportunity, item_id).shoot_start_date,
                fresh.get(Opportunity, item_id).shoot_end_date,
            )
            for item_id in OPPORTUNITY_IDS
        } == initial_dates
        assert fresh.scalar(select(func.count()).select_from(Opportunity)) == 8

    run(
        execute=True,
        reset=True,
        settings=authorized_settings(),
        session_factory=SessionLocal,
        as_of=AS_OF_B,
    )
    run(
        execute=True,
        reset=False,
        settings=authorized_settings(),
        session_factory=SessionLocal,
        as_of=AS_OF_B,
    )
    with SessionLocal() as fresh:
        assert fresh.get(
            Opportunity, OPPORTUNITY_IDS[0]
        ).submission_deadline == AS_OF_B + timedelta(hours=20)
        assert fresh.get(Opportunity, ordinary_id) is not None
        assert fresh.get(ActorProfile, PORTFOLIO_PROFILE_ID) is not None
        for model in (
            Submission,
            AuditionCalendarEvent,
            AuditionJournalEntry,
            AgentRecommendation,
            RecommendationFeedback,
            Asset,
        ):
            assert fresh.scalar(select(func.count()).select_from(model)) == 0
        assert fresh.scalar(select(func.count()).select_from(CastingGoal)) == 1
        assert fresh.scalar(select(func.count()).select_from(WatchList)) == 1
        assert fresh.scalar(select(func.count()).select_from(CareerMemory)) == 1


def test_opportunity_collision_rolls_back_entire_seed(db) -> None:
    from app.core.database import SessionLocal

    collision = Opportunity(
        id=OPPORTUNITY_IDS[-1],
        role="Ordinary Role",
        project="Ordinary Project",
        union="Non-Union",
        location="Chicago, IL",
        description="Ordinary user record occupying a reserved identity.",
        source_metadata={},
    )
    db.add(collision)
    db.commit()
    db.close()

    with pytest.raises(ValueError, match="Opportunity identity is already in use"):
        run(
            execute=True,
            reset=False,
            settings=authorized_settings(),
            session_factory=SessionLocal,
            as_of=AS_OF_A,
        )

    with SessionLocal() as fresh:
        assert (
            fresh.scalar(
                select(func.count())
                .select_from(Opportunity)
                .where(Opportunity.id.in_(OPPORTUNITY_IDS))
            )
            == 1
        )
        assert fresh.get(ActorProfile, PORTFOLIO_PROFILE_ID) is None
        assert fresh.scalar(select(func.count()).select_from(TravelPreference)) == 0
