from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select


pytestmark = pytest.mark.contract_smoke


def evidence(*, version="v1", authority="provider", url="https://generic.example/items/1"):
    from app.automation.discovery.source_evidence import (
        IdentityAuthority,
        SourceEvidence,
        SourceVersionField,
    )

    return SourceEvidence(
        source_key="generic_contract_source",
        source_url=url,
        external_source_id=None,
        identity_authority=IdentityAuthority(authority),
        version_fields=(SourceVersionField("version", version),) if version else (),
    )


def capabilities(*, trusted=True, automatic=True):
    from app.automation.discovery.source_evidence import SourceCapabilities
    from app.services.source_identity import SourceUrlPolicy

    return SourceCapabilities(
        trusted_source=trusted,
        automatic_non_acting_exclusion=automatic,
        url_policy=SourceUrlPolicy(),
    )


def classification(
    value="Crew Job", *, confidence="deterministic", acting=False, non_acting=True
):
    from app.automation.discovery.source_evidence import (
        ClassificationConfidence,
        SourceClassification,
        SourceClassificationEvidence,
    )

    return SourceClassificationEvidence(
        rule_key="generic_non_acting_rule",
        suggested_classification=SourceClassification(value),
        confidence_kind=ClassificationConfidence(confidence),
        acting_signal_present=acting,
        non_acting_signal_present=non_acting,
    )


def test_gate_records_new_then_existing_sighting_without_committing(db):
    from app.automation.discovery.source_exclusion_gate import (
        SourceExclusionGate,
        SourceExclusionGateOutcome,
    )
    from app.db.models import SourceExclusion

    gate = SourceExclusionGate(db)
    new_result = gate.evaluate(evidence(), capabilities(), classification())
    assert new_result.outcome is SourceExclusionGateOutcome.EXCLUDED_NEW
    assert db.scalar(select(func.count()).select_from(SourceExclusion)) == 1
    db.commit()

    existing = gate.evaluate(evidence(), capabilities())
    assert existing.outcome is SourceExclusionGateOutcome.EXCLUDED_EXISTING
    assert db.scalar(select(SourceExclusion)).times_seen == 2
    db.rollback()
    db.expire_all()
    assert db.scalar(select(SourceExclusion)).times_seen == 1


def test_gate_changed_version_and_expiry_follow_existing_service_contract(db):
    from app.automation.discovery.source_exclusion_gate import (
        SourceExclusionGate,
        SourceExclusionGateOutcome,
    )
    from app.db.models import SourceExclusion

    now = datetime(2026, 7, 18, tzinfo=timezone.utc)
    gate = SourceExclusionGate(db)
    gate.evaluate(evidence(), capabilities(), classification(), now=now)
    db.commit()

    changed_acting = gate.evaluate(
        evidence(version="v2"),
        capabilities(),
        classification("Acting Role", acting=True, non_acting=False),
        now=now + timedelta(days=1),
    )
    assert changed_acting.outcome is SourceExclusionGateOutcome.INELIGIBLE_FOR_EXCLUSION
    assert db.scalar(select(SourceExclusion)).content_version_hash != gate.identity_for(
        evidence(version="v2"), capabilities()
    ).content_version_hash

    changed_non_acting = gate.evaluate(
        evidence(version="v2"),
        capabilities(),
        classification("Non-Acting Job"),
        now=now + timedelta(days=2),
    )
    assert changed_non_acting.outcome is SourceExclusionGateOutcome.EXCLUDED_NEW
    assert db.scalar(select(SourceExclusion)).times_seen == 1
    db.rollback()

    row = db.scalar(select(SourceExclusion))
    row.expires_at = now + timedelta(days=1)
    db.commit()
    expired_now = now + timedelta(days=2)
    expired = gate.evaluate(evidence(), capabilities(), now=expired_now)
    assert expired.outcome is SourceExclusionGateOutcome.CONTINUE_PROCESSING
    reactivated = gate.evaluate(
        evidence(), capabilities(), classification(), now=expired_now
    )
    assert reactivated.outcome is SourceExclusionGateOutcome.EXCLUDED_NEW


@pytest.mark.parametrize(
    ("candidate", "caps", "classify"),
    [
        (evidence(authority="none"), capabilities(), classification()),
        (evidence(authority="user_supplied_url"), capabilities(), classification()),
        (evidence(version=""), capabilities(), classification()),
        (evidence(url=None), capabilities(), classification()),
        (evidence(), capabilities(trusted=False), classification()),
        (evidence(), capabilities(automatic=False), classification()),
        (evidence(), capabilities(), classification(confidence="probabilistic")),
        (evidence(), capabilities(), classification("Unknown", non_acting=False)),
        (evidence(), capabilities(), classification(acting=True)),
    ],
)
def test_ineligible_evidence_performs_no_write(db, candidate, caps, classify):
    from app.automation.discovery.source_exclusion_gate import (
        SourceExclusionGate,
        SourceExclusionGateOutcome,
    )
    from app.db.models import SourceExclusion

    result = SourceExclusionGate(db).evaluate(candidate, caps, classify)
    assert result.outcome is SourceExclusionGateOutcome.INELIGIBLE_FOR_EXCLUSION
    assert db.scalar(select(func.count()).select_from(SourceExclusion)) == 0


def test_gate_caller_rollback_removes_insert_and_version_update(db):
    from app.automation.discovery.source_exclusion_gate import SourceExclusionGate
    from app.db.models import SourceExclusion

    gate = SourceExclusionGate(db)
    gate.evaluate(evidence(), capabilities(), classification())
    db.rollback()
    assert db.scalar(select(func.count()).select_from(SourceExclusion)) == 0

    gate.evaluate(evidence(), capabilities(), classification())
    db.commit()
    original_hash = db.scalar(select(SourceExclusion)).content_version_hash
    gate.evaluate(evidence(version="v2"), capabilities(), classification())
    db.rollback()
    db.expire_all()
    assert db.scalar(select(SourceExclusion)).content_version_hash == original_hash
    assert db.execute(select(1)).scalar_one() == 1


def test_gate_creates_no_opportunity_or_derived_rows(db):
    from app.automation.discovery.source_exclusion_gate import SourceExclusionGate
    from app.db.models import BreakdownParseRun, BreakdownRole, Opportunity, SourceExclusion

    SourceExclusionGate(db).evaluate(evidence(), capabilities(), classification())
    assert db.scalar(select(func.count()).select_from(SourceExclusion)) == 1
    assert db.scalar(select(func.count()).select_from(Opportunity)) == 0
    assert db.scalar(select(func.count()).select_from(BreakdownRole)) == 0
    assert db.scalar(select(func.count()).select_from(BreakdownParseRun)) == 0
