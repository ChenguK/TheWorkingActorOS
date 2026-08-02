from sqlalchemy import func, select

import pytest


pytestmark = pytest.mark.contract_smoke


def _direct_notice():
    from app.automation.discovery.contracts import NormalizedOpportunity

    return NormalizedOpportunity(
        role="Maya",
        project="River City",
        union="SAG-AFTRA",
        location="New York, NY",
        description=(
            "Project: River City\nRole: Maya, Supporting, Black woman, ages 25-40. "
            "English language SAG-AFTRA feature film. Self-tape audition. "
            "Submission deadline: December 31, 2099."
        ),
        original_post_url="https://one-off.example.test/notices/river-city-maya",
        audition_type="Self-Tape",
        audition_travel_hours=0,
        breakdown_classification="Acting Role",
        source_name="Parallel Public Web Search",
        source_reliability_score=0.68,
        category="Film/TV Public Web Breakdown",
        source_metadata={
            "provider": "parallel",
            "source_type": "public_web_search",
            "source_url": "https://one-off.example.test/notices/river-city-maya",
            "page_title": "River City — Maya",
        },
        production_details={"project_type": "Feature Film", "union_status": "SAG-AFTRA"},
        role_details={
            "role_name": "Maya",
            "role_type": "Supporting",
            "submission_deadline": "December 31, 2099",
        },
    )


def _search_result(*items):
    from app.automation.discovery.public_web_search import PublicWebSearchResult

    return PublicWebSearchResult(
        configured=True,
        run=True,
        search_queries=["fixture query"],
        candidate_urls=[candidate.original_post_url for candidate in items],
        candidate_pages_found=len(items),
        candidate_reports=[
            {
                "page_title": candidate.source_metadata.get("page_title"),
                "url": candidate.original_post_url,
                "source": "Parallel Public Web Search",
                "decision": "Parsed",
                "rejection_reason": None,
            }
            for candidate in items
        ],
        normalized=list(items),
    )


def _configured_actor(db):
    from app.db.models import ActorProfile

    actor = ActorProfile(
        name="Fixture Actor",
        sag_status="SAG-AFTRA",
        union_status="SAG-AFTRA",
        current_location="New York, NY",
        playable_age_min=25,
        playable_age_max=40,
        skills=["Drama"],
        gender_identities=["Woman"],
        ethnicities=[],
        racial_identities=["Black / African American"],
        nationalities=[],
        languages=["English"],
        accents=[],
        disability_identities=[],
        included_role_types=["Supporting"],
        excluded_role_types=["Background", "Crew"],
    )
    db.add(actor)
    db.flush()
    return actor


def test_current_one_off_result_is_pending_without_domain_approval_or_public_web_commit(db):
    from app.automation.discovery.service import DiscoveryAutomationService
    from app.db.models import DiscoveryRun, Opportunity, SourceResearchItem

    _configured_actor(db)
    service = DiscoveryAutomationService(db)
    summary, routing = service._process_public_web_search_result(
        _search_result(_direct_notice()), "FilmTV", None, ["Match My Profile"], None
    )

    opportunity = db.scalar(select(Opportunity))
    source = db.scalar(select(SourceResearchItem))
    assert routing["created"] == 1
    assert routing["visible"] == 1
    assert summary["candidate_reports"][0]["decision"] == "Accepted"
    assert opportunity is not None
    assert opportunity.visibility_status == "visible"
    assert opportunity.breakdown_classification == "Acting Role"
    assert opportunity.original_post_url == "https://one-off.example.test/notices/river-city-maya"
    assert opportunity.source_metadata["source_url"] == opportunity.original_post_url
    assert "provider" not in opportunity.source_metadata
    assert "page_title" not in opportunity.source_metadata
    assert "excerpt" not in opportunity.source_metadata
    assert opportunity.demographic_match_status == "Match"
    assert "No explicit demographic mismatch" in opportunity.demographic_match_explanation
    assert source is not None
    assert source.status == "Suggested"
    assert source.approved_by_user is False
    assert source.approved_discovery_url is None
    assert source.suggested_specific_url == opportunity.original_post_url
    assert source.discovered_from_breakdown_id == opportunity.id
    assert source.discovery_reason == 'Matched breakdown found for "Maya" in "River City."'
    assert source.source_role_match_count == 1
    assert db.scalar(select(func.count()).select_from(DiscoveryRun)) == 0

    db.rollback()

    assert db.scalar(select(func.count()).select_from(Opportunity)) == 0
    assert db.scalar(select(func.count()).select_from(SourceResearchItem)) == 0
    assert db.execute(select(1)).scalar_one() == 1


def test_current_duplicate_identity_reuses_opportunity_and_does_not_merge_evidence_or_source_count(
    db,
):
    from app.automation.discovery.service import DiscoveryAutomationService
    from app.db.models import Opportunity, SourceResearchItem

    service = DiscoveryAutomationService(db)
    first_summary, first = service._process_public_web_search_result(
        _search_result(_direct_notice()), "FilmTV", None, ["Match My Profile"], None
    )
    second_item = _direct_notice()
    second_item.source_metadata["page_title"] = "Changed provider title"
    second_summary, second = service._process_public_web_search_result(
        _search_result(second_item), "FilmTV", None, ["Match My Profile"], None
    )

    opportunity = db.scalar(select(Opportunity))
    source = db.scalar(select(SourceResearchItem))
    assert first["created"] == 1
    assert first_summary["sources_suggested_for_approval"] == 1
    assert second["created"] == 0
    assert second["rejection_reasons_summary"]["duplicate"] == 1
    assert second_summary["candidate_reports"][0]["decision"] == "Rejected"
    assert second_summary["candidate_reports"][0]["rejection_reason"] == "Duplicate"
    assert db.scalar(select(func.count()).select_from(Opportunity)) == 1
    assert db.scalar(select(func.count()).select_from(SourceResearchItem)) == 1
    assert opportunity.source_metadata.get("source_url") == opportunity.original_post_url
    assert "page_title" not in opportunity.source_metadata
    assert source.source_role_match_count == 1
