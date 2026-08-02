from dataclasses import replace

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

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
            "Production Details\nProject: River City\nProject Type: Feature Film\n"
            "Union: SAG-AFTRA\nLocation: New York, NY\n\n"
            "Audition Information\nSelf-tape audition with virtual callback.\n\n"
            "Roles\nMaya (Supporting)\nBlack woman, ages 25-40, who speaks English. "
            "Maya is a determined public defender leading a feature-film drama.\n\n"
            "Submission Instructions\nSubmit headshot and resume by December 31, 2099."
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


class _FixtureSearch:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error

    def configured(self):
        return True

    def search(self, discovery_mode):
        assert discovery_mode == "FilmTV"
        if self.error:
            raise self.error
        return self.result


def _public_web_service(db, result=None, error=None):
    from app.automation.discovery.service import DiscoveryAutomationService

    service = DiscoveryAutomationService(db)
    service.public_web_search_factory = lambda _actor: _FixtureSearch(result, error)
    return service


def _run(service):
    return service._run_public_web_search("FilmTV", None, ["Match My Profile"], None)


def test_public_web_success_persists_run_opportunity_and_source_after_session_close(db):
    from app.core.database import SessionLocal
    from app.db.models import DiscoveryRun, Opportunity, SourceResearchItem

    _configured_actor(db)
    response = _run(_public_web_service(db, _search_result(_direct_notice())))

    summary = response["summary"]
    routing = response["result"]
    assert routing["created"] == 1
    assert routing["visible"] == 1
    assert summary["candidate_reports"][0]["outcome"] == "accept_visible"
    assert summary["candidate_reports"][0]["reason_code"] == "direct_eligible_notice"
    assert summary["candidate_reports"][0]["decision"] == "Accepted"
    db.close()

    with SessionLocal() as fresh:
        opportunity = fresh.scalar(select(Opportunity))
        source = fresh.scalar(select(SourceResearchItem))
        run = fresh.scalar(select(DiscoveryRun))
        assert opportunity is not None
        assert opportunity.visibility_status == "visible"
        assert opportunity.breakdown_classification == "Acting Role"
        assert (
            opportunity.original_post_url == "https://one-off.example.test/notices/river-city-maya"
        )
        assert opportunity.source_metadata["source_url"] == opportunity.original_post_url
        assert "provider" not in opportunity.source_metadata
        assert "page_title" not in opportunity.source_metadata
        assert "excerpt" not in opportunity.source_metadata
        assert opportunity.demographic_match_status == "Match"
        assert source is not None
        assert source.status == "Suggested"
        assert source.approved_by_user is False
        assert source.approved_discovery_url is None
        assert source.suggested_specific_url == opportunity.original_post_url
        assert source.discovered_from_breakdown_id == opportunity.id
        assert run is not None
        assert run.status == "succeeded"
        assert run.source_plugin_id is None
        assert run.total_found == 1
        assert run.total_saved == 1
        assert run.total_rejected == 0


def test_current_duplicate_identity_reuses_opportunity_and_does_not_merge_evidence_or_source_count(
    db,
):
    from app.automation.discovery.service import DiscoveryAutomationService
    from app.db.models import Opportunity, SourceResearchItem

    _configured_actor(db)
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
    assert second_summary["candidate_reports"][0]["outcome"] == "reject_discarded"
    assert second_summary["candidate_reports"][0]["reason_code"] == "duplicate_candidate"
    assert db.scalar(select(func.count()).select_from(Opportunity)) == 1
    assert db.scalar(select(func.count()).select_from(SourceResearchItem)) == 1
    assert opportunity.source_metadata.get("source_url") == opportunity.original_post_url
    assert "page_title" not in opportunity.source_metadata
    assert source.source_role_match_count == 1


def test_public_web_no_result_persists_one_successful_run(db):
    from app.db.models import DiscoveryRun, Opportunity, SourceResearchItem

    _configured_actor(db)
    result = _search_result()
    response = _run(_public_web_service(db, result))

    run = db.scalar(select(DiscoveryRun))
    assert response["result"]["total_found"] == 0
    assert run is not None
    assert run.status == "succeeded"
    assert run.total_found == 0
    assert run.total_saved == 0
    assert run.total_rejected == 0
    assert db.scalar(select(func.count()).select_from(Opportunity)) == 0
    assert db.scalar(select(func.count()).select_from(SourceResearchItem)) == 0


def test_public_web_mixed_run_persists_only_accepted_and_reviewable_candidates(db):
    from app.automation.discovery.decision_policy import PublicDiscoveryDecisionPolicy
    from app.db.models import DiscoveryRun, Opportunity, SourceResearchItem

    _configured_actor(db)
    accepted = _direct_notice()
    review = replace(
        _direct_notice(),
        role="Jordan",
        project="Harbor City",
        original_post_url="https://review.example.test/notices/harbor-city-jordan",
    )
    rejected = replace(
        _direct_notice(),
        role="Crew Listing",
        project="Studio Staff",
        original_post_url="https://rejected.example.test/jobs/studio-staff",
    )
    duplicate = replace(
        _direct_notice(),
        original_post_url="https://one-off.example.test/notices/river-city-maya-copy",
    )
    service = _public_web_service(db, _search_result(accepted, review, rejected, duplicate))
    real_policy = PublicDiscoveryDecisionPolicy()

    def decide(item, opportunity):
        if item.role == "Jordan":
            return real_policy.review("medium_parse_confidence", "The candidate requires review.")
        if item.role == "Crew Listing":
            return real_policy.reject("non_acting_job", "The candidate is not an acting role.")
        return real_policy.decide(item, opportunity)

    service.public_decision_policy.decide = decide

    response = _run(service)

    routing = response["result"]
    assert routing["created"] == 2
    assert routing["hidden"] == 1
    assert routing["discarded"] == 1
    assert routing["rejected"] == 1
    assert routing["rejection_reasons_summary"]["duplicate"] == 1
    opportunities = db.scalars(select(Opportunity).order_by(Opportunity.project)).all()
    assert [(item.project, item.visibility_status) for item in opportunities] == [
        ("Harbor City", "hidden"),
        ("River City", "visible"),
    ]
    assert db.scalar(select(func.count()).select_from(SourceResearchItem)) == 1
    run = db.scalar(select(DiscoveryRun))
    assert run.status == "succeeded"
    assert run.total_found == 4
    assert run.total_saved == 2
    assert run.opportunities_hidden == 1
    assert run.total_rejected == 1


def test_public_web_provider_failure_persists_failed_run_and_recovers_session(db):
    from app.db.models import DiscoveryRun, OpportunitySource

    _configured_actor(db)

    class ProviderFailureSearch(_FixtureSearch):
        def search(self, discovery_mode):
            db.add(
                OpportunitySource(
                    name="public-web-partial-source",
                    source_type="public_breakdowns",
                    priority_rank=99,
                    is_enabled=True,
                )
            )
            db.flush()
            raise RuntimeError("public provider exploded")

    service = _public_web_service(db)
    service.public_web_search_factory = lambda _actor: ProviderFailureSearch()

    with pytest.raises(RuntimeError, match="public provider exploded"):
        _run(service)

    run = db.scalar(select(DiscoveryRun))
    assert run is not None
    assert run.status == "failed"
    assert run.error_message == "public provider exploded"
    assert (
        db.scalar(
            select(func.count())
            .select_from(OpportunitySource)
            .where(OpportunitySource.name == "public-web-partial-source")
        )
        == 0
    )
    assert db.execute(select(1)).scalar_one() == 1


def test_public_web_candidate_rejection_is_successful_and_not_persisted(db):
    from app.automation.discovery.decision_policy import PublicDiscoveryDecisionPolicy
    from app.db.models import DiscoveryRun, Opportunity

    _configured_actor(db)
    service = _public_web_service(db, _search_result(_direct_notice()))
    service.public_decision_policy = PublicDiscoveryDecisionPolicy()
    service.public_decision_policy.decide = lambda *_args: service.public_decision_policy.reject(
        "non_acting_job", "The candidate is not an acting opportunity."
    )

    response = _run(service)

    assert response["result"]["discarded"] == 1
    assert response["result"]["created"] == 0
    assert db.scalar(select(func.count()).select_from(Opportunity)) == 0
    run = db.scalar(select(DiscoveryRun))
    assert run.status == "succeeded"
    assert run.total_saved == 0
    assert run.total_rejected == 1


def test_public_web_database_failure_rolls_back_domain_writes_and_persists_failed_run(db):
    from app.db.models import DiscoveryRun, Opportunity, SourceResearchItem

    _configured_actor(db)
    second = replace(
        _direct_notice(),
        role="Jordan",
        project="Harbor City",
        original_post_url="https://two-off.example.test/notices/harbor-city-jordan",
    )
    service = _public_web_service(db, _search_result(_direct_notice(), second))
    real_create = service._create_opportunity
    calls = 0

    def create_then_fail(item):
        nonlocal calls
        calls += 1
        if calls == 1:
            return real_create(item)
        from app.db.models import Opportunity

        db.add(
            Opportunity(
                role=None,
                project="Constraint Failure",
                union="SAG-AFTRA",
                location="New York, NY",
                description="Invalid public-web row",
            )
        )
        db.flush()
        raise AssertionError("unreachable")

    service._create_opportunity = create_then_fail

    with pytest.raises(IntegrityError):
        _run(service)

    assert db.scalar(select(func.count()).select_from(Opportunity)) == 0
    assert db.scalar(select(func.count()).select_from(SourceResearchItem)) == 0
    run = db.scalar(select(DiscoveryRun))
    assert run is not None
    assert run.status == "failed"
    assert db.execute(select(1)).scalar_one() == 1


def test_public_web_commit_failure_keeps_original_error_and_persists_failed_run(db, monkeypatch):
    from app.db.models import DiscoveryRun

    class CommitFailure(RuntimeError):
        pass

    _configured_actor(db)
    service = _public_web_service(db, _search_result())
    real_commit = db.commit
    commit_calls = 0

    def fail_first_commit():
        nonlocal commit_calls
        commit_calls += 1
        if commit_calls == 1:
            raise CommitFailure("public-web commit failed")
        real_commit()

    monkeypatch.setattr(db, "commit", fail_first_commit)

    with pytest.raises(CommitFailure, match="public-web commit failed"):
        _run(service)

    run = db.scalar(select(DiscoveryRun))
    assert run is not None
    assert run.status == "failed"
    assert run.error_message == "public-web commit failed"
    assert commit_calls == 2
    assert db.execute(select(1)).scalar_one() == 1


def test_public_web_failed_run_persistence_does_not_mask_provider_error(db, monkeypatch):
    _configured_actor(db)
    service = _public_web_service(db, error=ValueError("original public provider error"))

    def fail_commit():
        raise RuntimeError("failed public run could not commit")

    monkeypatch.setattr(db, "commit", fail_commit)

    with pytest.raises(ValueError, match="original public provider error"):
        _run(service)

    assert db.execute(select(1)).scalar_one() == 1


def test_public_web_success_commits_exactly_once(db, monkeypatch):
    _configured_actor(db)
    service = _public_web_service(db, _search_result())
    real_commit = db.commit
    commit_calls = 0

    def counted_commit():
        nonlocal commit_calls
        commit_calls += 1
        real_commit()

    monkeypatch.setattr(db, "commit", counted_commit)

    _run(service)

    assert commit_calls == 1
