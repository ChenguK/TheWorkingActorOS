from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.core.config import Settings
from app.db.models import (
    ActorProfile,
    Asset,
    AuditionCalendarEvent,
    Opportunity,
    Submission,
    TravelPreference,
)
from app.services.portfolio_seed_ownership_service import (
    PORTFOLIO_PROFILE_FIELDS,
    PORTFOLIO_PROFILE_ID,
    PORTFOLIO_TRAVEL_PREFERENCE_FIELDS,
    PORTFOLIO_TRAVEL_PREFERENCE_ID,
)
from scripts.seed_sanitized_portfolio import run


pytestmark = pytest.mark.contract_smoke


def authorized_settings() -> Settings:
    return Settings(
        _env_file=None,
        environment="development",
        sanitized_portfolio_seed_enabled=True,
    )


def test_profile_seed_is_durable_idempotent_and_reset_is_scoped(db, capsys) -> None:
    from app.core.database import SessionLocal

    ordinary = ActorProfile(
        name="Ordinary User Profile",
        sag_status="Unknown",
        union_status="Unknown",
        current_location="Chicago, IL",
        playable_age_min=30,
        playable_age_max=40,
    )
    db.add(ordinary)
    db.commit()
    ordinary_id = ordinary.id
    db.close()

    run(
        execute=True,
        reset=False,
        settings=authorized_settings(),
        session_factory=SessionLocal,
    )
    run(
        execute=True,
        reset=False,
        settings=authorized_settings(),
        session_factory=SessionLocal,
    )
    output = capsys.readouterr().out
    assert "ActorProfile: create" in output
    assert "ActorProfile: unchanged" in output
    assert "TravelPreference: create" in output
    assert "TravelPreference: unchanged" in output

    with SessionLocal() as fresh:
        profiles = list(fresh.scalars(select(ActorProfile).order_by(ActorProfile.id)))
        seeded = fresh.get(ActorProfile, PORTFOLIO_PROFILE_ID)
        travel = fresh.get(TravelPreference, PORTFOLIO_TRAVEL_PREFERENCE_ID)

        assert len(profiles) == 2
        assert fresh.get(ActorProfile, ordinary_id) is not None
        assert seeded is not None
        assert travel is not None
        for key, value in PORTFOLIO_PROFILE_FIELDS.items():
            assert getattr(seeded, key) == value
        for key, value in PORTFOLIO_TRAVEL_PREFERENCE_FIELDS.items():
            assert getattr(travel, key) == value
        assert travel.actor_profile_id == PORTFOLIO_PROFILE_ID
        assert fresh.scalar(select(func.count()).select_from(Opportunity)) == 0
        assert fresh.scalar(select(func.count()).select_from(Submission)) == 0
        assert fresh.scalar(select(func.count()).select_from(AuditionCalendarEvent)) == 0
        assert fresh.scalar(select(func.count()).select_from(Asset)) == 0

    run(
        execute=True,
        reset=True,
        settings=authorized_settings(),
        session_factory=SessionLocal,
    )

    with SessionLocal() as fresh:
        assert fresh.get(ActorProfile, PORTFOLIO_PROFILE_ID) is None
        assert fresh.get(TravelPreference, PORTFOLIO_TRAVEL_PREFERENCE_ID) is None
        assert fresh.get(ActorProfile, ordinary_id) is not None
