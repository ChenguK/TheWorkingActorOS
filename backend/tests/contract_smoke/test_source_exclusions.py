from __future__ import annotations

from datetime import datetime, timedelta, timezone
from threading import Barrier, Thread

import pytest
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import IntegrityError

pytestmark = pytest.mark.contract_smoke


def identity(*, version: str = "v1", external_id: str | None = "job-1", url: str | None = None):
    from app.services.source_identity import SourceIdentityService

    return SourceIdentityService.build_identity(
        source_name="playbill",
        external_source_id=external_id,
        raw_url=url,
        version_fields={"title": version},
    )


def test_source_exclusion_records_sighting_and_changed_version_is_not_suppressed(db):
    from app.db.models import SourceExclusion
    from app.services.source_exclusion_service import SourceExclusionService

    now = datetime(2026, 7, 18, tzinfo=timezone.utc)
    service = SourceExclusionService(db)
    created = service.record_confirmed_exclusion(
        identity(), classification="Crew Job", reason_code="provider_listing_rule", now=now
    )
    assert created.excluded is True
    db.commit()

    sighting = service.record_compatible_sighting(identity(), now=now + timedelta(hours=1))
    assert sighting.excluded is True
    db.commit()
    row = db.scalar(select(SourceExclusion))
    assert row is not None
    assert row.times_seen == 2
    assert row.first_seen_at == now
    assert row.last_seen_at == now + timedelta(hours=1)

    mismatch = service.record_compatible_sighting(
        identity(version="v2"), now=now + timedelta(hours=2)
    )
    assert mismatch.excluded is False
    db.commit()
    assert db.scalar(select(SourceExclusion)).times_seen == 2

    service.record_confirmed_exclusion(
        identity(version="v2"),
        classification="Non-Acting Job",
        reason_code="deterministic_classification",
        now=now + timedelta(hours=3),
    )
    db.commit()
    row = db.scalar(select(SourceExclusion))
    assert row.content_version_hash == identity(version="v2").content_version_hash
    assert row.classification == "Non-Acting Job"
    assert row.times_seen == 1
    assert row.first_seen_at == now + timedelta(hours=3)

    service.record_compatible_sighting(identity(version="v2"), now=now + timedelta(hours=4))
    db.rollback()
    db.expire_all()
    assert db.scalar(select(SourceExclusion)).times_seen == 1


def test_source_exclusion_url_expiry_reactivation_and_rollback(db):
    from app.db.models import SourceExclusion
    from app.services.source_exclusion_service import SourceExclusionService

    now = datetime(2026, 7, 18, tzinfo=timezone.utc)
    url_identity = identity(external_id=None, url="https://playbill.com/job/crew-1")
    service = SourceExclusionService(db)
    service.record_confirmed_exclusion(
        url_identity,
        classification="Non-Acting Job",
        reason_code="deterministic_classification",
        now=now,
    )
    db.commit()
    row = db.scalar(select(SourceExclusion))
    assert row.expires_at == now + timedelta(days=180)

    assert service.record_compatible_sighting(
        url_identity, now=now + timedelta(days=181)
    ).excluded is False
    service.record_confirmed_exclusion(
        url_identity,
        classification="Crew Job",
        reason_code="provider_listing_rule",
        now=now + timedelta(days=181),
    )
    db.rollback()
    db.expire_all()
    row = db.scalar(select(SourceExclusion))
    assert row.classification == "Non-Acting Job"
    assert row.times_seen == 1


def test_source_exclusion_database_constraints(db):
    from app.db.models import SourceExclusion

    now = datetime.now(timezone.utc)
    invalid = SourceExclusion(
        source_name="playbill",
        external_source_id=None,
        canonical_url_hash=None,
        content_version_hash="a" * 64,
        exclusion_type="confirmed_non_acting",
        classification="Crew Job",
        reason_code="provider_listing_rule",
        first_seen_at=now,
        last_seen_at=now,
        times_seen=1,
        expires_at=None,
    )
    db.add(invalid)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()

    for overrides in (
        {"times_seen": 0},
        {"classification": "Unknown"},
        {"reason_code": "user_rejected"},
        {"last_seen_at": now - timedelta(seconds=1)},
    ):
        values = {
            "source_name": "playbill",
            "external_source_id": f"constraint-{len(overrides)}-{overrides!s}",
            "canonical_url_hash": None,
            "content_version_hash": "b" * 64,
            "exclusion_type": "confirmed_non_acting",
            "classification": "Crew Job",
            "reason_code": "provider_listing_rule",
            "first_seen_at": now,
            "last_seen_at": now,
            "times_seen": 1,
            "expires_at": None,
        }
        values.update(overrides)
        db.add(SourceExclusion(**values))
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()


def test_source_exclusion_classification_gate_and_no_opportunity_write(db):
    from app.db.models import Opportunity, SourceExclusion
    from app.services.source_exclusion_service import SourceExclusionService

    service = SourceExclusionService(db)
    with pytest.raises(ValueError):
        service.record_confirmed_exclusion(
            identity(), classification="Unknown", reason_code="provider_listing_rule"
        )
    with pytest.raises(ValueError):
        service.record_confirmed_exclusion(
            identity(), classification="Crew Job", reason_code="user_rejected"
        )
    assert db.scalar(select(func.count()).select_from(SourceExclusion)) == 0
    assert db.scalar(select(func.count()).select_from(Opportunity)) == 0


def test_source_exclusion_concurrent_confirmations_converge(clean_database):
    from app.core.database import SessionLocal
    from app.db.models import SourceExclusion
    from app.services.source_exclusion_service import SourceExclusionService

    gate = Barrier(2)
    results: list[bool] = []
    errors: list[BaseException] = []
    shared_identity = identity(external_id="concurrent-job")

    def worker() -> None:
        session = SessionLocal()
        try:
            gate.wait(timeout=5)
            result = SourceExclusionService(session).record_confirmed_exclusion(
                shared_identity,
                classification="Crew Job",
                reason_code="provider_listing_rule",
            )
            session.commit()
            results.append(result.excluded)
            assert session.execute(text("SELECT 1")).scalar_one() == 1
        except BaseException as exc:  # pragma: no cover - surfaced by parent assertion
            errors.append(exc)
            session.rollback()
        finally:
            session.close()

    threads = [Thread(target=worker), Thread(target=worker)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert not any(thread.is_alive() for thread in threads)
    assert errors == []
    assert results == [True, True]
    with SessionLocal() as session:
        rows = session.scalars(select(SourceExclusion)).all()
        assert len(rows) == 1
        assert rows[0].times_seen == 2


def test_source_exclusion_schema_matches_migration(db):
    inspector = inspect(db.bind)
    columns = {column["name"]: column for column in inspector.get_columns("source_exclusions")}
    assert set(columns) == {
        "id",
        "source_name",
        "external_source_id",
        "canonical_url_hash",
        "content_version_hash",
        "exclusion_type",
        "classification",
        "reason_code",
        "first_seen_at",
        "last_seen_at",
        "times_seen",
        "expires_at",
        "created_at",
        "updated_at",
    }
    checks = {constraint["name"] for constraint in inspector.get_check_constraints("source_exclusions")}
    assert checks == {
        "ck_source_exclusions_identity",
        "ck_source_exclusions_weak_expiry",
        "ck_source_exclusions_times_seen",
        "ck_source_exclusions_seen_order",
        "ck_source_exclusions_expiry_order",
        "ck_source_exclusions_type",
        "ck_source_exclusions_classification",
        "ck_source_exclusions_reason",
    }
    indexes = {index["name"]: index for index in inspector.get_indexes("source_exclusions")}
    assert indexes["uq_source_exclusions_source_external_id"]["unique"] is True
    assert indexes["uq_source_exclusions_source_url_hash"]["unique"] is True


def test_source_exclusion_partial_uniqueness_and_weak_expiry(db):
    from app.db.models import SourceExclusion

    now = datetime.now(timezone.utc)

    def row(*, external_id=None, url_hash=None, expiry=None):
        return SourceExclusion(
            source_name="playbill",
            external_source_id=external_id,
            canonical_url_hash=url_hash,
            content_version_hash="c" * 64,
            exclusion_type="confirmed_non_acting",
            classification="Crew Job",
            reason_code="provider_listing_rule",
            first_seen_at=now,
            last_seen_at=now,
            times_seen=1,
            expires_at=expiry,
        )

    db.add(row(external_id="duplicate-id"))
    db.commit()
    db.add(row(external_id="duplicate-id"))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()

    db.add(row(url_hash="d" * 64, expiry=now + timedelta(days=1)))
    db.commit()
    db.add(row(url_hash="d" * 64, expiry=now + timedelta(days=1)))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()

    db.add(row(url_hash="e" * 64, expiry=None))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_zz_source_exclusion_migration_downgrades_and_reupgrades(db):
    from alembic import command
    from alembic.config import Config
    from app.core.database import engine

    db.close()
    config = Config("alembic.ini")
    try:
        command.downgrade(config, "0054_protect_opportunity_delete")
        assert "source_exclusions" not in inspect(engine).get_table_names()
    finally:
        command.upgrade(config, "head")
    assert "source_exclusions" in inspect(engine).get_table_names()
