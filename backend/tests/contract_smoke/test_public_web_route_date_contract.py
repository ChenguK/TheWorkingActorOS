from types import SimpleNamespace

from sqlalchemy import func, select

import pytest


pytestmark = pytest.mark.contract_smoke


class _NoRegistryProviders:
    def list(self):
        return []


class _FixtureParallelClient:
    def __init__(self, results=None, error=None):
        self.results = list(results or [])
        self.error = error
        self.calls = []

    def search(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(results=self.results)


def _provider_result(url, title, snippet):
    return SimpleNamespace(
        url=url,
        title=title,
        excerpts=[snippet],
        publish_date="2026-08-01",
        arbitrary_payload={"discard": "PROVIDER-PAYLOAD-SENTINEL"},
    )


def _acting_notice(
    project="River City", role="Maya", deadline="December 31, 2035", audition="Self-tape"
):
    deadline_text = f"Submission Deadline: {deadline}" if deadline else ""
    return f"""Production Details
Project: {project}
Project Type: Feature Film
Union: SAG-AFTRA
Location: New York, NY
Audition Information
{audition} audition with callback.
Roles
Role: {role}
{role} (Supporting)
Black woman, ages 25-40, who speaks English. {role} is a determined professional leading a feature-film drama.
Submission Instructions
Submit headshot and resume through this public casting notice.
{deadline_text}"""


def _actor(db):
    from app.db.models import ActorProfile

    actor = ActorProfile(
        name="Fictional Route Actor",
        sag_status="SAG-AFTRA",
        union_status="SAG-AFTRA",
        current_location="New York, NY",
        playable_age_min=25,
        playable_age_max=40,
        skills=["Drama"],
        gender_identities=["Woman"],
        racial_identities=["Black / African American"],
        languages=["English"],
        included_role_types=["Supporting"],
        excluded_role_types=["Crew"],
    )
    db.add(actor)
    db.commit()
    return actor


def _install(monkeypatch, provider, pages):
    from app.automation.discovery import service as service_module
    from app.automation.discovery.public_content_fetch import (
        PublicContentFetchOutcome,
        PublicContentFetchResult,
    )
    from app.automation.discovery.public_web_search import PublicWebBreakdownSearch

    monkeypatch.setattr(service_module, "DiscoveryPluginRegistry", _NoRegistryProviders)
    monkeypatch.setattr(PublicWebBreakdownSearch, "configured", lambda _self: True)
    monkeypatch.setattr(PublicWebBreakdownSearch, "_client", lambda _self: provider)
    monkeypatch.setattr(
        PublicWebBreakdownSearch,
        "_fetch_visible_text",
        lambda _self, url: PublicContentFetchResult(
            PublicContentFetchOutcome.SUCCESS, text=pages[url]
        ),
    )


def test_route_accepts_future_deadline_stored_only_in_structured_details(client, db, monkeypatch):
    from app.db.models import Opportunity

    _actor(db)

    url = "https://casting.example.test/notices/river-city-maya"
    provider = _FixtureParallelClient(
        [_provider_result(url, "River City — Maya", "Bounded fictional provider context.")]
    )
    _install(monkeypatch, provider, {url: _acting_notice()})

    response = client.post(
        "/api/v1/automation/discovery/run",
        params=[("mode", "FilmTV"), ("search_modes", "Match My Profile")],
    )

    assert response.status_code == 200
    candidate = response.json()["discovery_report"]["candidates"][0]
    opportunity = db.scalar(select(Opportunity).where(Opportunity.original_post_url == url))
    assert candidate["outcome"] == "accept_visible", (
        candidate["reason_code"],
        [
            (check["name"], check["reason"])
            for check in opportunity.source_metadata["trust_verification"]["checks"]
            if check["status"] == "warning"
        ],
    )
    assert candidate["reason_code"] == "direct_eligible_notice"
    assert len(provider.calls) == 1
    assert opportunity.submission_deadline is None
    assert opportunity.production_details["submission_deadline"] == "December 31, 2035"
    date_check = next(
        check
        for check in opportunity.source_metadata["trust_verification"]["checks"]
        if check["name"] == "Date Verification"
    )
    assert date_check["status"] == "pass"
    assert "No submission" not in date_check["reason"]


def test_route_proves_complete_mocked_public_web_decision_and_durability_slice(
    client, db, monkeypatch
):
    from app.core.database import SessionLocal
    from app.db.models import DiscoveryRun, Opportunity, SourceResearchItem

    _actor(db)
    accepted = "https://casting.example.test/notices/river-city-maya"
    hidden = "https://review.example.test/notices/harbor-city-jordan"
    travel = "https://travel.example.test/notices/lake-city-rina"
    crew = "https://jobs.example.test/production-coordinator"
    expired = "https://expired.example.test/notices/old-city-lee"
    duplicate = "https://casting.example.test/notices/river-city-maya-copy"
    provider = _FixtureParallelClient(
        [
            _provider_result(accepted + "#first", "River City — Maya", "First context wins."),
            _provider_result(hidden, "Harbor City — Jordan", "Missing deadline context."),
            _provider_result(travel, "Lake City — Rina", "In-person context."),
            _provider_result(crew, "Production Coordinator", "Crew context."),
            _provider_result(expired, "Old City — Lee", "Expired context."),
            _provider_result(duplicate, "River City duplicate", "Duplicate context."),
            _provider_result(accepted + "#later", "Later title", "Later context."),
        ]
    )
    pages = {
        accepted: _acting_notice(),
        hidden: _acting_notice("Harbor City", "Jordan", deadline=None),
        travel: _acting_notice("Lake City", "Rina", audition="In-person"),
        crew: "Production company hiring a casting coordinator and production assistant for a full-time staff and crew job.",
        expired: _acting_notice("Old City", "Lee", deadline="January 1, 2020"),
        duplicate: _acting_notice(),
    }
    _install(monkeypatch, provider, pages)

    response = client.post(
        "/api/v1/automation/discovery/run",
        params=[("mode", "FilmTV"), ("search_modes", "Match My Profile")],
    )

    assert response.status_code == 200
    payload = response.json()
    candidates = {item["url"]: item for item in payload["discovery_report"]["candidates"]}
    assert (candidates[accepted]["outcome"], candidates[accepted]["reason_code"]) == (
        "accept_visible",
        "direct_eligible_notice",
    )
    assert candidates[accepted]["provider_evidence"]["title"] == "River City — Maya"
    assert (candidates[hidden]["outcome"], candidates[hidden]["reason_code"]) == (
        "review_hidden",
        "missing_deadline",
    )
    assert (candidates[travel]["outcome"], candidates[travel]["reason_code"]) == (
        "review_hidden",
        "travel_uncertain",
    )
    assert candidates[crew]["outcome"] == "reject_discarded"
    assert candidates[expired]["reason_code"] == "expired_notice"
    assert candidates[duplicate]["reason_code"] == "duplicate_candidate"
    assert len(provider.calls) == 1
    assert provider.calls[0]["advanced_settings"] == {"max_results": 10}
    assert len(provider.calls[0]["search_queries"]) <= 6
    assert all(len(query) <= 220 for query in provider.calls[0]["search_queries"])
    assert "Later title" not in str(payload)
    assert "PROVIDER-PAYLOAD-SENTINEL" not in str(payload)

    db.close()
    with SessionLocal() as fresh:
        run = fresh.scalar(select(DiscoveryRun))
        opportunities = fresh.scalars(select(Opportunity).order_by(Opportunity.project)).all()
        sources = fresh.scalars(select(SourceResearchItem)).all()
        assert fresh.scalar(select(func.count()).select_from(DiscoveryRun)) == 1
        assert run.status == "succeeded"
        evidence = run.run_payload["public_web_evidence"]
        assert evidence["version"] == 1
        assert [item["canonical_url"] for item in evidence["items"]] == [
            accepted,
            hidden,
            travel,
            crew,
            expired,
            duplicate,
        ]
        assert len(evidence["items"]) <= 10
        assert [(item.project, item.visibility_status) for item in opportunities] == [
            ("Harbor City", "hidden"),
            ("Lake City", "hidden"),
            ("River City", "visible"),
        ]
        assert len(sources) == 1
        assert sources[0].status == "Suggested"
        assert sources[0].approved_by_user is False
        assert sources[0].approved_discovery_url is None
        assert all("provider_evidence" not in item.source_metadata for item in opportunities)
        assert "PROVIDER-PAYLOAD-SENTINEL" not in str(run.run_payload)


def test_route_persists_empty_evidence_on_success(client, db, monkeypatch):
    from app.core.database import SessionLocal
    from app.db.models import DiscoveryRun, Opportunity, SourceResearchItem

    _actor(db)
    provider = _FixtureParallelClient([])
    _install(monkeypatch, provider, {})
    response = client.post(
        "/api/v1/automation/discovery/run",
        params=[("mode", "FilmTV"), ("search_modes", "Match My Profile")],
    )
    assert response.status_code == 200
    db.close()
    with SessionLocal() as fresh:
        run = fresh.scalar(select(DiscoveryRun))
        assert run.run_payload["public_web_evidence"] == {"version": 1, "items": []}
        assert fresh.scalar(select(func.count()).select_from(Opportunity)) == 0
        assert fresh.scalar(select(func.count()).select_from(SourceResearchItem)) == 0


def test_route_provider_failure_has_no_partial_domain_state(client, db, monkeypatch):
    from app.core.database import SessionLocal
    from app.db.models import DiscoveryRun, Opportunity, SourceResearchItem

    _actor(db)
    provider = _FixtureParallelClient(error=RuntimeError("fixture provider unavailable"))
    _install(monkeypatch, provider, {})
    with pytest.raises(RuntimeError, match="fixture provider unavailable"):
        client.post(
            "/api/v1/automation/discovery/run",
            params=[("mode", "FilmTV"), ("search_modes", "Match My Profile")],
        )
    db.close()
    with SessionLocal() as fresh:
        run = fresh.scalar(select(DiscoveryRun))
        assert run.status == "failed"
        assert "public_web_evidence" not in run.run_payload
        assert fresh.scalar(select(func.count()).select_from(Opportunity)) == 0
        assert fresh.scalar(select(func.count()).select_from(SourceResearchItem)) == 0
