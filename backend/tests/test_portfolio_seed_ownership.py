from __future__ import annotations

import json
from unittest.mock import MagicMock
from uuid import UUID

from app.db.models import Opportunity
from app.services.portfolio_seed_ownership_service import (
    PORTFOLIO_SEED_NAMESPACE,
    PortfolioSeedOwnershipService,
)
from scripts import cleanup_source_and_demo_data, seed_sanitized_portfolio


OWNED_ID = UUID("00000000-0000-0000-0000-000000000101")
USER_ID = UUID("00000000-0000-0000-0000-000000000202")


def build_opportunity(*, opportunity_id: UUID, owned: bool) -> Opportunity:
    opportunity = Opportunity(
        id=opportunity_id,
        role="Supporting Performer",
        project="Harbor Lights",
        union="Non-Union",
        location="New York, NY",
        description="A fictional dramatic film role.",
        source_type="Manual Entry",
        source_metadata={},
        is_demo_data=False,
    )
    if owned:
        PortfolioSeedOwnershipService.mark_portfolio_owned(opportunity)
    return opportunity


def scalar_result(*items: Opportunity) -> MagicMock:
    result = MagicMock()
    result.all.return_value = list(items)
    return result


def test_portfolio_metadata_survives_json_serialization_and_preserves_normal_status() -> None:
    opportunity = build_opportunity(opportunity_id=OWNED_ID, owned=True)

    serialized = json.loads(json.dumps(opportunity.source_metadata))

    assert serialized == {"portfolio_seed": {"namespace": PORTFOLIO_SEED_NAMESPACE}}
    assert opportunity.is_demo_data is False


def test_ordinary_user_opportunity_is_never_portfolio_owned() -> None:
    opportunity = build_opportunity(opportunity_id=USER_ID, owned=False)
    opportunity.source_metadata = {"portfolio_seed": {"namespace": "another-dataset"}}

    assert PortfolioSeedOwnershipService.is_portfolio_owned(opportunity) is False


def test_demo_flag_alone_never_establishes_portfolio_ownership() -> None:
    opportunity = build_opportunity(opportunity_id=USER_ID, owned=False)
    opportunity.is_demo_data = True

    assert PortfolioSeedOwnershipService.is_portfolio_owned(opportunity) is False


def test_dry_run_performs_zero_writes(monkeypatch) -> None:
    owned = build_opportunity(opportunity_id=OWNED_ID, owned=True)
    db = MagicMock()
    db.scalars.return_value = scalar_result(owned)
    monkeypatch.setattr(seed_sanitized_portfolio, "SessionLocal", lambda: db)

    seed_sanitized_portfolio.run(execute=False, reset=True)

    db.delete.assert_not_called()
    db.flush.assert_not_called()
    db.commit.assert_not_called()
    db.rollback.assert_not_called()
    db.close.assert_called_once_with()


def test_reset_only_deletes_records_that_still_have_exact_ownership() -> None:
    owned = build_opportunity(opportunity_id=OWNED_ID, owned=True)
    user = build_opportunity(opportunity_id=USER_ID, owned=False)
    db = MagicMock()
    db.scalars.side_effect = [scalar_result(owned), scalar_result(owned, user)]
    service = PortfolioSeedOwnershipService(db)

    plan = service.plan(reset=True)
    service.apply_reset(plan)

    assert plan.remove_opportunity_ids == (OWNED_ID,)
    db.delete.assert_called_once_with(owned)


def test_repeated_reset_runs_are_idempotent() -> None:
    owned = build_opportunity(opportunity_id=OWNED_ID, owned=True)
    first_db = MagicMock()
    first_db.scalars.side_effect = [scalar_result(owned), scalar_result(owned)]
    first_service = PortfolioSeedOwnershipService(first_db)
    first_plan = first_service.plan(reset=True)
    first_service.apply_reset(first_plan)

    second_db = MagicMock()
    second_db.scalars.return_value = scalar_result()
    second_service = PortfolioSeedOwnershipService(second_db)
    second_plan = second_service.plan(reset=True)
    second_service.apply_reset(second_plan)

    assert first_plan.remove_count == 1
    assert second_plan.remove_count == 0
    first_db.delete.assert_called_once_with(owned)
    second_db.delete.assert_not_called()


def test_correctly_named_portfolio_record_avoids_legacy_demo_cleanup() -> None:
    opportunity = build_opportunity(opportunity_id=OWNED_ID, owned=True)

    assert cleanup_source_and_demo_data.is_demo_breakdown(opportunity) is False


def test_script_rolls_back_failed_execute(monkeypatch) -> None:
    db = MagicMock()
    db.scalars.side_effect = RuntimeError("planned database failure")
    monkeypatch.setattr(seed_sanitized_portfolio, "SessionLocal", lambda: db)

    try:
        seed_sanitized_portfolio.run(execute=True, reset=True)
    except RuntimeError as exc:
        assert str(exc) == "planned database failure"
    else:
        raise AssertionError("expected the planned failure")

    db.commit.assert_not_called()
    db.rollback.assert_called_once_with()
    db.close.assert_called_once_with()


def test_execute_commits_exactly_once(monkeypatch) -> None:
    db = MagicMock()
    db.scalars.return_value = scalar_result()
    monkeypatch.setattr(seed_sanitized_portfolio, "SessionLocal", lambda: db)

    seed_sanitized_portfolio.run(execute=True, reset=False)

    db.commit.assert_called_once_with()
    db.rollback.assert_not_called()
    db.close.assert_called_once_with()
