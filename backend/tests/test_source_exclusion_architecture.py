from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_source_exclusion_foundation_has_no_unapproved_integration():
    backend = ROOT / "backend"
    model = (backend / "app/db/models/source_exclusion.py").read_text()
    service = (backend / "app/services/source_exclusion_service.py").read_text()
    identity = (backend / "app/services/source_identity.py").read_text()

    assert "Opportunity" not in model
    assert "relationship(" not in model
    assert "JSON" not in model
    assert "commit(" not in service
    assert "app.automation.discovery" not in service
    assert "requests" not in identity
    assert "httpx" not in identity

    production = [path for path in (backend / "app").rglob("*.py") if path.name not in {
        "source_exclusion.py",
        "source_exclusion_service.py",
        "source_exclusion_gate.py",
        "source_identity.py",
        "__init__.py",
    }]
    references = [path for path in production if "SourceExclusion" in path.read_text()]
    assert references == []

    frontend = ROOT / "frontend/src"
    assert not any("sourceExclusion" in path.read_text() for path in frontend.rglob("*.ts*"))


def test_discovery_transaction_correction_does_not_expand_provider_or_candidate_ownership():
    discovery = ROOT / "backend/app/automation/discovery"
    service = (discovery / "service.py").read_text()
    contracts = (discovery / "contracts.py").read_text()
    provider_files = [
        path
        for path in discovery.glob("*.py")
        if path.name
        not in {
            "service.py",
            "source_evidence.py",
            "source_exclusion_gate.py",
            "__init__.py",
        }
    ]

    assert "begin_nested(" not in service
    assert "savepoint" not in service.lower()
    assert "SourceExclusionService" not in service
    assert "SourceIdentityService" not in service
    assert "SourceCandidate" not in contracts
    assert "SourceListingCandidate" not in contracts
    assert all("from sqlalchemy.orm import Session" not in path.read_text() for path in provider_files)
    assert all("session.commit(" not in path.read_text() for path in provider_files)


def test_source_exclusion_gate_is_provider_neutral_dormant_infrastructure():
    backend = ROOT / "backend"
    discovery = backend / "app/automation/discovery"
    gate = (discovery / "source_exclusion_gate.py").read_text()
    evidence = (discovery / "source_evidence.py").read_text()

    assert "SourceIdentityService" in gate
    assert "SourceExclusionService" in gate
    assert ".commit(" not in gate
    assert ".rollback(" not in gate
    assert "begin_nested(" not in gate
    assert "SessionLocal" not in gate
    assert "Opportunity" not in gate
    assert "playbill" not in gate.lower()
    assert "parallel" not in gate.lower()
    assert "playbill" not in evidence.lower()
    assert "parallel" not in evidence.lower()

    consumers = [
        path
        for path in backend.joinpath("app").rglob("*.py")
        if path.name not in {"source_exclusion_gate.py"}
        and "SourceExclusionGate" in path.read_text()
    ]
    assert consumers == []

    providers = [
        discovery / "public_sources.py",
        discovery / "public_web_search.py",
        discovery / "providers.py",
    ]
    assert all("source_exclusion_gate" not in path.read_text() for path in providers)
    assert "source_exclusion_gate" not in (discovery / "service.py").read_text()

    api = backend / "app/api"
    assert not any("SourceEvidence" in path.read_text() for path in api.rglob("*.py"))
    frontend = ROOT / "frontend/src"
    assert not any("SourceEvidence" in path.read_text() for path in frontend.rglob("*.ts*"))
