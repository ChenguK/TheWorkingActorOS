from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.agents.executive_agent import ExecutiveAgent
from app.services.command_center_service import CommandCenterService
from app.services.operations_service import OperationsService


AS_OF = datetime(2027, 1, 15, 15, 0, tzinfo=timezone.utc)


def _service_for_orchestration():
    db = MagicMock()
    actor = SimpleNamespace(id="actor-id")
    db.scalars.return_value.first.return_value = actor
    return CommandCenterService(db), actor


def test_snapshot_preserves_refresh_read_visit_order():
    service, actor = _service_for_orchestration()
    calls: list[str] = []
    payload = {"today_opportunities": []}

    service.refresh_signals = MagicMock(side_effect=lambda: calls.append("refresh"))
    service._last_visit_at = MagicMock(return_value=AS_OF)
    service.read_snapshot = MagicMock(side_effect=lambda **_kwargs: calls.append("read") or payload)
    service.record_visit = MagicMock(side_effect=lambda _actor, _now: calls.append("visit"))

    with patch.object(
        OperationsService,
        "today_platform_check_ins",
        side_effect=lambda: calls.append("platform-refresh") or [],
    ):
        result = service.snapshot(as_of=AS_OF)

    assert result is payload
    assert calls == ["refresh", "platform-refresh", "read", "visit"]
    service.read_snapshot.assert_called_once_with(actor=actor, as_of=AS_OF, since_at=AS_OF)


@pytest.mark.parametrize(
    ("failure_at", "expected_calls"),
    [
        ("refresh", ["refresh"]),
        ("read", ["refresh", "platform-refresh", "read"]),
        ("visit", ["refresh", "platform-refresh", "read", "visit"]),
    ],
)
def test_snapshot_failure_stops_at_existing_boundary(failure_at, expected_calls):
    service, _actor = _service_for_orchestration()
    calls: list[str] = []

    def step(name, result=None):
        calls.append(name)
        if name == failure_at:
            raise RuntimeError(f"{name} failed")
        return result

    service.refresh_signals = MagicMock(side_effect=lambda: step("refresh"))
    service._last_visit_at = MagicMock(return_value=AS_OF)
    service.read_snapshot = MagicMock(side_effect=lambda **_kwargs: step("read", {}))
    service.record_visit = MagicMock(side_effect=lambda _actor, _now: step("visit"))

    with patch.object(
        OperationsService,
        "today_platform_check_ins",
        side_effect=lambda: step("platform-refresh", []),
    ):
        with pytest.raises(RuntimeError, match=f"{failure_at} failed"):
            service.snapshot(as_of=AS_OF)

    assert calls == expected_calls


def test_platform_check_in_reader_executes_only_a_select():
    db = MagicMock()
    db.execute.return_value.all.return_value = []

    result = OperationsService(db).read_today_platform_check_ins(as_of=AS_OF)

    assert result == []
    db.execute.assert_called_once()
    db.add.assert_not_called()
    db.flush.assert_not_called()
    db.commit.assert_not_called()
    db.rollback.assert_not_called()


def test_signal_refresh_preserves_enrichment_alert_nudge_and_commit_boundary():
    db = MagicMock()
    opportunity = SimpleNamespace(id="opportunity-id")
    db.scalars.return_value = [opportunity]
    service = CommandCenterService(db)
    service._ensure_outcome_nudges = MagicMock()
    service._ensure_material_gap_alerts = MagicMock()

    with patch(
        "app.services.command_center_service.OpportunityIntelligenceService"
    ) as intelligence_type:
        service.refresh_signals()

    intelligence_type.return_value.enrich.assert_called_once_with(opportunity)
    service._ensure_outcome_nudges.assert_called_once_with()
    service._ensure_material_gap_alerts.assert_called_once_with()
    db.commit.assert_called_once_with()


def test_signal_creation_failure_prevents_refresh_commit():
    db = MagicMock()
    db.scalars.return_value = []
    service = CommandCenterService(db)
    service._ensure_outcome_nudges = MagicMock(side_effect=RuntimeError("nudge failed"))

    with pytest.raises(RuntimeError, match="nudge failed"):
        service.refresh_signals()

    db.commit.assert_not_called()


def test_visit_commit_failure_remains_visible_to_the_caller():
    db = MagicMock()
    db.commit.side_effect = RuntimeError("visit commit failed")
    state = SimpleNamespace(last_dashboard_visit_at=None)
    service = CommandCenterService(db)
    service._chief_of_staff_state = MagicMock(return_value=state)

    with pytest.raises(RuntimeError, match="visit commit failed"):
        service.record_visit(None, AS_OF)

    assert state.last_dashboard_visit_at == AS_OF
    db.commit.assert_called_once_with()


def test_executive_read_path_uses_only_persisted_platform_check_ins():
    db = MagicMock()
    scalar_result = MagicMock()
    scalar_result.__iter__.return_value = iter([])
    scalar_result.first.return_value = None
    db.scalars.return_value = scalar_result
    db.scalar.return_value = 0

    with (
        patch.object(
            OperationsService, "read_today_platform_check_ins", return_value=[]
        ) as read_check_ins,
        patch.object(OperationsService, "today_platform_check_ins") as mutate_check_ins,
    ):
        ExecutiveAgent(db).read_top_priorities(as_of=AS_OF)

    read_check_ins.assert_called_once_with(as_of=AS_OF)
    mutate_check_ins.assert_not_called()
    db.add.assert_not_called()
    db.flush.assert_not_called()
    db.commit.assert_not_called()
    db.rollback.assert_not_called()


def test_read_boundaries_require_timezone_aware_as_of():
    naive = datetime(2027, 1, 15, 15, 0)

    with pytest.raises(ValueError, match="timezone-aware"):
        ExecutiveAgent(MagicMock()).read_top_priorities(as_of=naive)
    with pytest.raises(ValueError, match="timezone-aware"):
        OperationsService(MagicMock()).read_today_platform_check_ins(as_of=naive)
