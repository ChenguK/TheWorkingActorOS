from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from app.db.models import ActorProfile, Opportunity
from app.services.portfolio_seed_ownership_service import (
    PORTFOLIO_PROFILE_FIELDS,
    PORTFOLIO_PROFILE_ID,
)
from app.services.sanitized_portfolio_manifest import build_sanitized_portfolio_manifest
from app.services.sanitized_portfolio_opportunity_service import (
    PORTFOLIO_OPPORTUNITY_COLLISION_ERROR,
    PORTFOLIO_OPPORTUNITY_RESET_DEPENDENCY_ERROR,
    SanitizedPortfolioOpportunityService,
    TEMPORAL_OPPORTUNITY_FIELDS,
)
from scripts import cleanup_source_and_demo_data


AS_OF_A = datetime(2032, 2, 3, 16, 0, tzinfo=timezone.utc)
AS_OF_B = AS_OF_A + timedelta(days=90)


def profile() -> ActorProfile:
    return ActorProfile(id=PORTFOLIO_PROFILE_ID, **PORTFOLIO_PROFILE_FIELDS)


def scalar_rows(*records: Opportunity) -> MagicMock:
    result = MagicMock()
    result.all.return_value = list(records)
    return result


def persisted_opportunity(*, as_of: datetime = AS_OF_A, index: int = 0) -> Opportunity:
    service = SanitizedPortfolioOpportunityService(MagicMock())
    definition = build_sanitized_portfolio_manifest(as_of).opportunities[index]
    return Opportunity(
        id=definition.id,
        **service._non_temporal_fields(definition),
        **service._temporal_fields(definition),
    )


def test_missing_profile_and_reserved_identity_collision_fail_closed() -> None:
    missing_db = MagicMock()
    missing_db.get.return_value = None
    with pytest.raises(ValueError, match="ActorProfile must exist"):
        SanitizedPortfolioOpportunityService(missing_db).plan(as_of=AS_OF_A)

    collision = persisted_opportunity()
    collision.source_metadata = {}
    collision_db = MagicMock()
    collision_db.get.return_value = profile()
    collision_db.scalars.return_value = scalar_rows(collision)
    with pytest.raises(ValueError, match=PORTFOLIO_OPPORTUNITY_COLLISION_ERROR):
        SanitizedPortfolioOpportunityService(collision_db).plan(as_of=AS_OF_A)
    collision_db.add.assert_not_called()


def test_later_as_of_is_unchanged_and_preserves_all_temporal_fields() -> None:
    records = tuple(persisted_opportunity(index=index) for index in range(7))
    before = {
        item.id: tuple(getattr(item, field) for field in TEMPORAL_OPPORTUNITY_FIELDS)
        for item in records
    }
    db = MagicMock()
    db.get.return_value = profile()
    db.scalars.return_value = scalar_rows(*records)

    plan = SanitizedPortfolioOpportunityService(db).plan(as_of=AS_OF_B)

    assert plan.unchanged_count == 7
    assert plan.update_count == 0
    assert before == {
        item.id: tuple(getattr(item, field) for field in TEMPORAL_OPPORTUNITY_FIELDS)
        for item in records
    }
    db.add.assert_not_called()
    db.flush.assert_not_called()
    db.commit.assert_not_called()
    db.rollback.assert_not_called()


def test_non_temporal_update_preserves_dates_and_derived_state() -> None:
    record = persisted_opportunity()
    original_dates = tuple(getattr(record, field) for field in TEMPORAL_OPPORTUNITY_FIELDS)
    record.role = "Outdated fictional role"
    record.urgency_score = 73
    record.quality_score = 88
    record.priority = "Urgent"
    record.source_metadata = {
        **record.source_metadata,
        "workflow_sentinel": "preserve",
    }
    record.role_details = {**record.role_details, "enrichment_sentinel": "preserve"}
    db = MagicMock()
    db.get.return_value = profile()
    db.scalars.return_value = scalar_rows(record)
    service = SanitizedPortfolioOpportunityService(db)

    plan = service.plan(as_of=AS_OF_B)
    service.apply(plan)

    assert plan.update_count == 1
    assert record.role == "Forensic Analyst"
    assert tuple(getattr(record, field) for field in TEMPORAL_OPPORTUNITY_FIELDS) == original_dates
    assert (record.urgency_score, record.quality_score, record.priority) == (73, 88, "Urgent")
    assert record.source_metadata["workflow_sentinel"] == "preserve"
    assert record.role_details["enrichment_sentinel"] == "preserve"
    db.commit.assert_not_called()


def test_reset_fails_closed_before_delete_when_dependency_exists() -> None:
    record = persisted_opportunity()
    db = MagicMock()
    db.scalars.return_value = scalar_rows(record)
    db.scalar.return_value = "dependent-id"

    with pytest.raises(ValueError, match=PORTFOLIO_OPPORTUNITY_RESET_DEPENDENCY_ERROR):
        SanitizedPortfolioOpportunityService(db).reset_owned_opportunities()

    db.delete.assert_not_called()


def test_all_persisted_definitions_avoid_legacy_cleanup_classification() -> None:
    for index in range(7):
        assert (
            cleanup_source_and_demo_data.is_demo_breakdown(persisted_opportunity(index=index))
            is False
        )
