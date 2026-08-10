from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.db.models import ActorProfile, CareerMemory
from app.services.executive_intelligence_service import ExecutiveIntelligenceService
from app.services.portfolio_seed_ownership_service import (
    PORTFOLIO_PROFILE_FIELDS,
    PORTFOLIO_PROFILE_ID,
)
from app.services.sanitized_portfolio_career_targeting_service import (
    SanitizedPortfolioCareerTargetingService,
)
from app.services.sanitized_portfolio_manifest import build_sanitized_portfolio_manifest


AS_OF = datetime(2033, 1, 2, 12, 0, tzinfo=timezone.utc)


def test_dry_plan_performs_no_writes_or_mutations() -> None:
    db = MagicMock()
    db.get.side_effect = [
        ActorProfile(id=PORTFOLIO_PROFILE_ID, **PORTFOLIO_PROFILE_FIELDS),
        None,
        None,
    ]
    db.scalars.return_value.first.return_value = None

    plan = SanitizedPortfolioCareerTargetingService(db).plan(
        build_sanitized_portfolio_manifest(AS_OF)
    )

    assert (plan.casting_goal_action, plan.watch_list_action, plan.career_memory_action) == (
        "create",
        "create",
        "create",
    )
    db.add.assert_not_called()
    db.flush.assert_not_called()
    db.commit.assert_not_called()
    db.rollback.assert_not_called()


def test_public_memory_creation_still_commits_but_primitive_does_not() -> None:
    actor = ActorProfile(id=PORTFOLIO_PROFILE_ID, **PORTFOLIO_PROFILE_FIELDS)
    primitive_db = MagicMock()
    primitive_db.scalars.return_value.first.return_value = None
    memory, created = ExecutiveIntelligenceService(
        primitive_db
    ).get_or_create_memory_without_commit(actor)
    assert created is True
    assert memory.actor_profile_id == PORTFOLIO_PROFILE_ID
    primitive_db.add.assert_called_once_with(memory)
    primitive_db.commit.assert_not_called()

    public_db = MagicMock()
    public_db.scalars.return_value.first.return_value = None
    created_memory = ExecutiveIntelligenceService(public_db).get_or_create_memory(actor)
    public_db.add.assert_called_once_with(created_memory)
    public_db.commit.assert_called_once_with()
    public_db.refresh.assert_called_once_with(created_memory)


def test_public_existing_memory_preserves_no_commit_behavior() -> None:
    actor = ActorProfile(id=PORTFOLIO_PROFILE_ID, **PORTFOLIO_PROFILE_FIELDS)
    memory = CareerMemory(actor_profile_id=PORTFOLIO_PROFILE_ID)
    db = MagicMock()
    db.scalars.return_value.first.return_value = memory

    assert ExecutiveIntelligenceService(db).get_or_create_memory(actor) is memory
    db.commit.assert_not_called()
