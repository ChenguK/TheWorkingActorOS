from types import SimpleNamespace

from sqlalchemy import select

import pytest


pytestmark = pytest.mark.contract_smoke


class _NoRegistryProviders:
    def list(self):
        return []


class _FixtureParallelClient:
    def __init__(self, url):
        self.url = url
        self.calls = []

    def search(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            results=[
                SimpleNamespace(
                    url=self.url,
                    title="River City — Maya",
                    excerpts=["Bounded fictional provider context."],
                    publish_date="2026-08-01",
                )
            ]
        )


def _acting_notice():
    return """Production Details
Project: River City
Project Type: Feature Film
Union: SAG-AFTRA
Location: New York, NY
Audition Information
Self-tape audition with virtual callback.
Roles
Role: Maya
Maya (Supporting)
Black woman, ages 25-40, who speaks English. Maya is a determined public defender leading a feature-film drama.
Submission Instructions
Submit headshot and resume by December 31, 2035.
Submission Deadline: December 31, 2035"""


def test_route_accepts_future_deadline_stored_only_in_structured_details(client, db, monkeypatch):
    from app.automation.discovery import service as service_module
    from app.automation.discovery.public_content_fetch import (
        PublicContentFetchOutcome,
        PublicContentFetchResult,
    )
    from app.automation.discovery.public_web_search import PublicWebBreakdownSearch
    from app.db.models import ActorProfile, Opportunity

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

    url = "https://casting.example.test/notices/river-city-maya"
    provider = _FixtureParallelClient(url)
    monkeypatch.setattr(service_module, "DiscoveryPluginRegistry", _NoRegistryProviders)
    monkeypatch.setattr(PublicWebBreakdownSearch, "configured", lambda _self: True)
    monkeypatch.setattr(PublicWebBreakdownSearch, "_client", lambda _self: provider)
    monkeypatch.setattr(
        PublicWebBreakdownSearch,
        "_fetch_visible_text",
        lambda _self, candidate_url: PublicContentFetchResult(
            PublicContentFetchOutcome.SUCCESS,
            text=_acting_notice() if candidate_url == url else None,
        ),
    )

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
