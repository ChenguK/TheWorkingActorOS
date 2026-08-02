from types import SimpleNamespace

import pytest

from app.automation.discovery.contracts import NormalizedOpportunity
from app.automation.discovery.public_web_search import PublicWebSearchResult
from app.automation.discovery.service import DiscoveryAutomationService


def item(**overrides) -> NormalizedOpportunity:
    values = {
        "role": "Maya",
        "project": "River City",
        "union": "SAG-AFTRA",
        "location": "New York, NY",
        "description": "Feature film casting notice seeking a Black woman age 25-40 who speaks English for Maya.",
        "original_post_url": "https://public.example.test/notices/river-city-maya",
        "audition_type": "Self-Tape",
        "audition_travel_hours": 0,
        "breakdown_classification": "Acting Role",
        "source_metadata": {
            "provider": "parallel",
            "source_url": "https://public.example.test/notices/river-city-maya",
        },
        "production_details": {"project_type": "Feature Film"},
        "role_details": {
            "language_requirements": "English",
            "submission_deadline": "December 1, 2035",
        },
    }
    values.update(overrides)
    return NormalizedOpportunity(**values)


def result(*items: NormalizedOpportunity) -> PublicWebSearchResult:
    return PublicWebSearchResult(
        configured=True,
        run=True,
        search_queries=["fixture query"],
        candidate_urls=[candidate.original_post_url for candidate in items],
        candidate_pages_found=len(items),
        candidate_reports=[
            {
                "page_title": candidate.project,
                "url": candidate.original_post_url,
                "source": "Parallel Public Web Search",
                "decision": "Parsed",
                "rejection_reason": None,
            }
            for candidate in items
        ],
        normalized=list(items),
    )


@pytest.mark.parametrize(
    (
        "visibility",
        "hidden_by_rule",
        "hidden_reason",
        "was_created",
        "expected_result",
        "expected_outcome",
        "expected_reason_code",
    ),
    [
        (
            "visible",
            None,
            None,
            True,
            {
                "created": 1,
                "visible": 1,
                "hidden": 0,
                "travel_exceptions": 0,
                "discarded": 0,
                "rejected": 0,
            },
            "accept_visible",
            "direct_eligible_notice",
        ),
        (
            "hidden",
            "needs_date_review",
            "Needs Date Review before recommendation.",
            True,
            {
                "created": 1,
                "visible": 0,
                "hidden": 1,
                "travel_exceptions": 0,
                "discarded": 0,
                "rejected": 0,
            },
            "review_hidden",
            "missing_deadline",
        ),
        (
            "travel_exception",
            "travel_exception",
            "Outside saved audition travel preference.",
            True,
            {
                "created": 1,
                "visible": 0,
                "hidden": 0,
                "travel_exceptions": 1,
                "discarded": 0,
                "rejected": 0,
            },
            "review_hidden",
            "travel_exception_review",
        ),
        (
            "discarded",
            "dealbreaker_demographic_mismatch",
            "Rejected because no parsed role overlaps the actor profile.",
            True,
            {
                "created": 0,
                "visible": 0,
                "hidden": 0,
                "travel_exceptions": 0,
                "discarded": 1,
                "rejected": 1,
            },
            "reject_discarded",
            "hard_demographic_mismatch",
        ),
        (
            "visible",
            None,
            None,
            False,
            {
                "created": 0,
                "visible": 1,
                "hidden": 0,
                "travel_exceptions": 0,
                "discarded": 0,
                "rejected": 0,
            },
            "reject_discarded",
            "duplicate_candidate",
        ),
    ],
)
def test_current_public_web_routing_matrix(
    visibility,
    hidden_by_rule,
    hidden_reason,
    was_created,
    expected_result,
    expected_outcome,
    expected_reason_code,
):
    deleted = []
    service = DiscoveryAutomationService(db=SimpleNamespace(delete=deleted.append))
    opportunity = SimpleNamespace(
        visibility_status=visibility,
        hidden_by_rule=hidden_by_rule,
        hidden_reason=hidden_reason,
        source_metadata={"breakdown_parse_confidence": 68 if visibility == "hidden" else 82},
    )
    service._create_opportunity = lambda _item: (opportunity, was_created)
    service._suggest_source_from_public_breakdown = lambda _opportunity: was_created

    summary, routing = service._process_public_web_search_result(
        result(item()), "FilmTV", None, ["Match My Profile"], None
    )

    for key, value in expected_result.items():
        assert routing[key] == value
    assert summary["candidate_reports"][0]["outcome"] == expected_outcome
    assert summary["candidate_reports"][0]["reason_code"] == expected_reason_code
    assert summary["candidate_reports"][0]["parser_confidence"] == (
        68 if visibility == "hidden" else 82
    )
    assert summary["sources_suggested_for_approval"] == (
        1 if visibility == "visible" and was_created else 0
    )
    assert deleted == (
        [opportunity] if expected_outcome == "reject_discarded" and was_created else []
    )


def test_current_expired_result_is_rejected_before_persistence():
    expired = item(role_details={"submission_deadline": "January 1, 2020"})
    service = DiscoveryAutomationService(db=None)
    persisted = []
    service._create_opportunity = lambda candidate: persisted.append(candidate)

    summary, routing = service._process_public_web_search_result(
        result(expired), "FilmTV", None, ["Match My Profile"], None
    )

    assert persisted == []
    assert routing["created"] == 0
    assert routing["rejected"] == 1
    assert routing["rejection_reasons_summary"]["deadline_expired"] == 1
    assert summary["candidate_reports"][0]["decision"] == "Rejected"
    assert summary["candidate_reports"][0]["outcome"] == "reject_discarded"
    assert summary["candidate_reports"][0]["reason_code"] == "expired_notice"


def test_ambiguous_medium_confidence_result_routes_to_hidden_review():
    ambiguous = item(
        role="Performer",
        project="Casting Advice Article",
        description="An article discussing actors, auditions, lead roles, and self tapes without an actionable role.",
        original_post_url="https://news.example.test/articles/casting-advice",
        source_metadata={
            "provider": "parallel",
            "source_url": "https://news.example.test/articles/casting-advice",
        },
    )
    service = DiscoveryAutomationService(db=None)
    opportunity = SimpleNamespace(
        visibility_status="visible",
        hidden_by_rule=None,
        hidden_reason=None,
        source_metadata={"breakdown_parse_confidence": 55},
    )
    service._create_opportunity = lambda _item: (opportunity, True)
    service._suggest_source_from_public_breakdown = lambda _opportunity: True

    summary, routing = service._process_public_web_search_result(
        result(ambiguous), "FilmTV", None, ["Match My Profile"], None
    )

    assert routing["visible"] == 0
    assert routing["hidden"] == 1
    assert opportunity.visibility_status == "hidden"
    candidate = summary["candidate_reports"][0]
    assert candidate["decision"] == "Needs Review"
    assert candidate["outcome"] == "review_hidden"
    assert candidate["reason_code"] == "medium_parse_confidence"
    assert candidate["parser_confidence"] == 55
    assert candidate["rejection_reason"] is None


def test_pre_routed_page_kinds_are_counted_without_creating_opportunities():
    search_result = PublicWebSearchResult(
        configured=True,
        run=True,
        candidate_pages_found=3,
        candidates_rejected=1,
        candidate_reports=[
            {
                "url": "https://public.example.test/directory",
                "page_kind": "multi_listing_index",
                "decision": "Needs Review",
                "outcome": "review_hidden",
                "reason_code": "multi_listing_index",
            },
            {
                "url": "https://public.example.test/resource",
                "page_kind": "casting_resource",
                "decision": "Rejected",
                "outcome": "reject_discarded",
                "reason_code": "casting_resource_page",
            },
            {
                "url": "https://public.example.test/uncertain",
                "page_kind": "uncertain",
                "decision": "Needs Review",
                "outcome": "review_hidden",
                "reason_code": "uncertain_page_kind",
            },
        ],
    )
    service = DiscoveryAutomationService(db=None)
    service._create_opportunity = lambda _candidate: pytest.fail(
        "pre-routed pages must not reach Opportunity creation"
    )

    summary, routing = service._process_public_web_search_result(
        search_result, "FilmTV", None, ["Match My Profile"], None
    )

    assert routing["created"] == 0
    assert routing["hidden"] == 2
    assert routing["discarded"] == 1
    assert routing["rejected"] == 1
    assert summary["candidate_pages_parsed"] == 0
