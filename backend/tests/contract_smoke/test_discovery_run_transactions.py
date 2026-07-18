from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError


pytestmark = pytest.mark.contract_smoke


class _Registry:
    def __init__(self, plugin) -> None:
        self.plugin = plugin

    def get(self, implementation_key: str):
        assert implementation_key == self.plugin.implementation_key
        return self.plugin


class _Plugin:
    name = "Transaction Contract Source"
    implementation_key = "transaction_contract_source"

    def __init__(self, discover) -> None:
        self.discover = discover

    def normalize(self, raw_items):
        return raw_items

    def deduplicate(self, items):
        return items

    def validate(self, _item):
        return True


def _service(db, plugin):
    from app.automation.discovery.service import DiscoveryAutomationService
    from app.db.models import DiscoverySourcePlugin

    plugin_record = DiscoverySourcePlugin(
        name=plugin.name,
        priority_rank=100,
        source_type="public_breakdowns",
        implementation_key=plugin.implementation_key,
        reliability_score=0.8,
    )
    db.add(plugin_record)
    db.commit()

    service = DiscoveryAutomationService(db)
    service.registry = _Registry(plugin)
    service._provider_settings = lambda _key: SimpleNamespace(
        enabled=True,
        provider_metadata={},
        health_status="available",
        health_message=None,
        last_health_check_at=None,
    )
    service._research_source_allowed = lambda _settings: True
    service._plugin_record = lambda _key: plugin_record
    return service


def test_provider_exception_rolls_back_partial_write_and_persists_one_failed_run(db):
    from app.db.models import DiscoveryRun, OpportunitySource

    def discover():
        db.add(
            OpportunitySource(
                name="must-roll-back",
                source_type="public_breakdowns",
                priority_rank=99,
                is_enabled=True,
            )
        )
        db.flush()
        raise RuntimeError("provider exploded")

    service = _service(db, _Plugin(discover))

    with pytest.raises(RuntimeError, match="provider exploded"):
        service.run_source("transaction_contract_source")

    runs = db.scalars(select(DiscoveryRun)).all()
    assert len(runs) == 1
    assert runs[0].status == "failed"
    assert runs[0].error_message == "provider exploded"
    assert runs[0].finished_at is not None
    assert runs[0].completed_at == runs[0].finished_at
    assert runs[0].opportunities_found == 0
    assert runs[0].opportunities_created == 0
    assert runs[0].opportunities_hidden == 0
    assert runs[0].total_found == 0
    assert runs[0].total_saved == 0
    assert runs[0].total_rejected == 0
    assert db.scalar(
        select(func.count()).select_from(OpportunitySource).where(OpportunitySource.name == "must-roll-back")
    ) == 0
    assert db.execute(select(1)).scalar_one() == 1


def test_database_failure_rolls_back_opportunity_and_child_then_persists_failed_run(db):
    from app.automation.discovery.contracts import NormalizedOpportunity
    from app.db.models import BreakdownRole, DiscoveryRun, Opportunity, OpportunitySource

    item = NormalizedOpportunity(
        role="Transaction Role",
        project="Transaction Project",
        union="SAG-AFTRA",
        location="New York, NY",
        description="A valid acting breakdown used only for transaction characterization.",
        original_post_url="https://example.test/transaction-role",
        audition_type="Virtual",
        audition_travel_hours=None,
        breakdown_classification="Acting Role",
    )
    service = _service(db, _Plugin(lambda: [item]))
    service._matches_mode = lambda *_args: True
    service._matches_search_intent = lambda *_args: True

    def partial_write_then_fail(_item):
        source = OpportunitySource(
            name="transaction-child-source",
            source_type="public_breakdowns",
            priority_rank=99,
            is_enabled=True,
        )
        db.add(source)
        db.flush()
        opportunity = Opportunity(
            opportunity_source_id=source.id,
            role="Partial Opportunity",
            project="Must Roll Back",
            union="SAG-AFTRA",
            location="New York, NY",
            description="Partial write",
            normalized_key="transaction-partial-opportunity",
        )
        db.add(opportunity)
        db.flush()
        db.add(BreakdownRole(breakdown_id=opportunity.id, role_name="Partial Role"))
        db.flush()
        db.add(
            Opportunity(
                role=None,
                project="Constraint Failure",
                union="SAG-AFTRA",
                location="New York, NY",
                description="Invalid role triggers a real PostgreSQL failed transaction.",
            )
        )
        db.flush()
        raise AssertionError("unreachable")

    service._create_opportunity = partial_write_then_fail

    with pytest.raises(IntegrityError):
        service.run_source("transaction_contract_source")

    run = db.scalar(select(DiscoveryRun))
    assert run is not None
    assert run.status == "failed"
    assert "NotNullViolation" in (run.error_message or "") or "not-null" in (run.error_message or "").lower()
    assert db.scalar(select(func.count()).select_from(Opportunity)) == 0
    assert db.scalar(select(func.count()).select_from(BreakdownRole)) == 0
    assert db.scalar(
        select(func.count()).select_from(OpportunitySource).where(
            OpportunitySource.name == "transaction-child-source"
        )
    ) == 0
    assert db.execute(select(1)).scalar_one() == 1


def test_commit_time_failure_is_recovered_and_original_error_remains_primary(db, monkeypatch):
    from app.db.models import DiscoveryRun

    class CommitFailure(RuntimeError):
        pass

    service = _service(db, _Plugin(lambda: []))
    real_commit = db.commit
    commit_calls = 0

    def fail_first_commit():
        nonlocal commit_calls
        commit_calls += 1
        if commit_calls == 1:
            raise CommitFailure("final commit failed")
        real_commit()

    monkeypatch.setattr(db, "commit", fail_first_commit)

    with pytest.raises(CommitFailure, match="final commit failed"):
        service.run_source("transaction_contract_source")

    run = db.scalar(select(DiscoveryRun))
    assert run is not None
    assert run.status == "failed"
    assert run.error_message == "final commit failed"
    assert commit_calls == 2
    assert db.execute(select(1)).scalar_one() == 1


def test_failed_status_persistence_failure_does_not_mask_original_error(db, monkeypatch):
    service = _service(db, _Plugin(lambda: (_ for _ in ()).throw(ValueError("original provider error"))))

    def fail_commit():
        raise RuntimeError("failed status could not commit")

    monkeypatch.setattr(db, "commit", fail_commit)

    with pytest.raises(ValueError, match="original provider error"):
        service.run_source("transaction_contract_source")

    assert db.execute(select(1)).scalar_one() == 1


def test_success_path_still_commits_once_and_returns_existing_shape(db, monkeypatch):
    service = _service(db, _Plugin(lambda: []))
    real_commit = db.commit
    commit_calls = 0

    def counted_commit():
        nonlocal commit_calls
        commit_calls += 1
        real_commit()

    monkeypatch.setattr(db, "commit", counted_commit)

    result = service.run_source("transaction_contract_source")

    assert commit_calls == 1
    assert result == {
        "source": "Transaction Contract Source",
        "created": 0,
        "hidden": 0,
        "travel_exceptions": 0,
        "discarded": 0,
        "visible": 0,
        "rejected": 0,
        "total_found": 0,
        "rejection_reasons_summary": {
            "mode_mismatch": 0,
            "validation_failed": 0,
            "hidden": 0,
            "travel_exception": 0,
            "discarded": 0,
            "duplicate": 0,
            "demo_data": 0,
            "search_intent_mismatch": 0,
            "deadline_expired": 0,
            "needs_date_review": 0,
            "source_result_in_role_search": 0,
        },
        "skipped": False,
    }
