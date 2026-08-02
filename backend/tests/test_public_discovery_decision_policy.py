from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest

from app.automation.discovery.decision_policy import (
    PUBLIC_DISCOVERY_ACCEPT_CONFIDENCE,
    PUBLIC_DISCOVERY_MAX_EXPLANATION_LENGTH,
    PublicDiscoveryDecisionPolicy,
    PublicDiscoveryOutcome,
)


def candidate(**overrides):
    values = {
        "role": "Maya",
        "project": "River City",
        "union": "SAG-AFTRA",
        "location": "New York, NY",
        "description": (
            "Feature film casting call seeking actors. Role: Maya. "
            "Submit by December 1, 2035 for this self-tape opportunity."
        ),
        "breakdown_classification": "Acting Role",
        "production_details": {
            "project_type": "Feature Film",
            "submission_deadline": "2035-12-01",
        },
        "role_details": {"submission_deadline": "2035-12-01"},
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def opportunity(**overrides):
    values = {
        "visibility_status": "visible",
        "hidden_by_rule": None,
        "hidden_reason": None,
        "source_metadata": {"breakdown_parse_confidence": 82},
        "submission_deadline": "2035-12-01",
        "audition_deadline": None,
        "location": "New York, NY",
        "shoot_location": None,
        "audition_location": None,
        "union": "SAG-AFTRA",
        "project_type": "Feature Film",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.parametrize(
    ("item_overrides", "opportunity_overrides", "outcome", "reason"),
    [
        ({}, {}, PublicDiscoveryOutcome.ACCEPT_VISIBLE, "direct_eligible_notice"),
        (
            {"union": "Non-Union"},
            {"union": "Non-Union"},
            PublicDiscoveryOutcome.ACCEPT_VISIBLE,
            "direct_eligible_notice",
        ),
        (
            {"union": "SAG-Eligible"},
            {"union": "SAG-Eligible"},
            PublicDiscoveryOutcome.ACCEPT_VISIBLE,
            "direct_eligible_notice",
        ),
        (
            {},
            {"source_metadata": {"breakdown_parse_confidence": 69}},
            PublicDiscoveryOutcome.REVIEW_HIDDEN,
            "medium_parse_confidence",
        ),
        (
            {"role": "Performer"},
            {},
            PublicDiscoveryOutcome.REVIEW_HIDDEN,
            "missing_actionable_details",
        ),
        (
            {
                "project": "Casting Advice Article",
                "description": "An article with casting advice for actors.",
            },
            {},
            PublicDiscoveryOutcome.REVIEW_HIDDEN,
            "ambiguous_casting_content",
        ),
        (
            {"role_details": {}, "production_details": {"project_type": "Feature Film"}},
            {"submission_deadline": None},
            PublicDiscoveryOutcome.REVIEW_HIDDEN,
            "missing_deadline",
        ),
        (
            {"location": "See source"},
            {"location": None},
            PublicDiscoveryOutcome.REVIEW_HIDDEN,
            "missing_location",
        ),
        (
            {"union": "Unknown"},
            {"union": "Unknown"},
            PublicDiscoveryOutcome.REVIEW_HIDDEN,
            "union_uncertain",
        ),
        (
            {"production_details": {"submission_deadline": "2035-12-01"}},
            {"project_type": None},
            PublicDiscoveryOutcome.REVIEW_HIDDEN,
            "uncertain_project_type",
        ),
        (
            {},
            {"visibility_status": "travel_exception", "hidden_by_rule": "travel_exception"},
            PublicDiscoveryOutcome.REVIEW_HIDDEN,
            "travel_exception_review",
        ),
        (
            {},
            {"visibility_status": "hidden", "hidden_by_rule": "audition_location_needs_info"},
            PublicDiscoveryOutcome.REVIEW_HIDDEN,
            "travel_uncertain",
        ),
        (
            {"breakdown_classification": "Crew Job"},
            {"source_metadata": {"breakdown_parse_confidence": 55}},
            PublicDiscoveryOutcome.REJECT_DISCARDED,
            "crew_or_staff_listing",
        ),
        (
            {"breakdown_classification": "Non-Acting Job"},
            {},
            PublicDiscoveryOutcome.REJECT_DISCARDED,
            "non_acting_job",
        ),
        (
            {},
            {"visibility_status": "discarded", "hidden_by_rule": "deadline_expired"},
            PublicDiscoveryOutcome.REJECT_DISCARDED,
            "expired_notice",
        ),
        (
            {},
            {
                "visibility_status": "discarded",
                "hidden_by_rule": "dealbreaker_demographic_mismatch",
            },
            PublicDiscoveryOutcome.REJECT_DISCARDED,
            "hard_demographic_mismatch",
        ),
        (
            {},
            {"visibility_status": "discarded", "hidden_by_rule": "dealbreaker_role_type"},
            PublicDiscoveryOutcome.REJECT_DISCARDED,
            "excluded_role_type",
        ),
        (
            {},
            {"visibility_status": "discarded", "hidden_by_rule": "dealbreaker_availability"},
            PublicDiscoveryOutcome.REJECT_DISCARDED,
            "required_date_unavailable",
        ),
        (
            {},
            {"visibility_status": "discarded", "hidden_by_rule": "dealbreaker_audition_travel"},
            PublicDiscoveryOutcome.REJECT_DISCARDED,
            "travel_limit_exceeded",
        ),
        (
            {},
            {
                "visibility_status": "discarded",
                "hidden_by_rule": "dealbreaker_eligibility",
                "hidden_reason": "Required language is not in the actor profile.",
            },
            PublicDiscoveryOutcome.REJECT_DISCARDED,
            "required_language_missing",
        ),
        (
            {},
            {"source_metadata": {"breakdown_parse_confidence": 0}},
            PublicDiscoveryOutcome.REJECT_DISCARDED,
            "unusable_parse_confidence",
        ),
    ],
)
def test_public_discovery_decision_table(item_overrides, opportunity_overrides, outcome, reason):
    decision = PublicDiscoveryDecisionPolicy().decide(
        candidate(**item_overrides), opportunity(**opportunity_overrides)
    )

    assert decision.outcome == outcome
    assert decision.reason_code == reason


def test_material_trust_warning_routes_to_review_but_non_material_warning_does_not():
    policy = PublicDiscoveryDecisionPolicy()
    material = opportunity(
        source_metadata={
            "breakdown_parse_confidence": 82,
            "trust_verification": {
                "status": "Needs Info",
                "checks": [
                    {"name": "Platform Verification", "status": "warning", "reason": "Review"}
                ],
            },
        }
    )
    optional = opportunity(
        source_metadata={
            "breakdown_parse_confidence": 82,
            "trust_verification": {
                "status": "Needs Info",
                "checks": [
                    {"name": "Contact Verification", "status": "warning", "reason": "Missing"}
                ],
            },
        }
    )

    assert policy.decide(candidate(), material).reason_code == "trust_warning"
    assert policy.decide(candidate(), optional).outcome == PublicDiscoveryOutcome.ACCEPT_VISIBLE


@pytest.mark.parametrize(
    "overrides",
    [
        {"visibility_status": "discarded", "hidden_by_rule": "deadline_expired", "location": None},
        {
            "visibility_status": "discarded",
            "hidden_by_rule": "dealbreaker_demographic_mismatch",
            "source_metadata": {"breakdown_parse_confidence": 55},
        },
    ],
)
def test_hard_failure_precedence_cannot_be_overridden_by_uncertainty(overrides):
    decision = PublicDiscoveryDecisionPolicy().decide(candidate(), opportunity(**overrides))
    assert decision.outcome == PublicDiscoveryOutcome.REJECT_DISCARDED


def test_decision_is_deterministic_bounded_plain_text_and_has_one_primary_reason():
    policy = PublicDiscoveryDecisionPolicy()
    item = candidate(role="Performer", union="Unknown", location="See source")
    record = opportunity(
        union="Unknown",
        location=None,
        submission_deadline=None,
        source_metadata={"breakdown_parse_confidence": 55},
    )

    first = policy.decide(deepcopy(item), deepcopy(record))
    second = policy.decide(deepcopy(item), deepcopy(record))

    assert first == second
    assert first.reason_code == "medium_parse_confidence"
    assert first.supporting_reason_codes == (
        "missing_actionable_details",
        "missing_location",
        "union_uncertain",
    )
    assert len(first.explanation) <= PUBLIC_DISCOVERY_MAX_EXPLANATION_LENGTH
    assert "<" not in first.explanation
    assert first.as_report_fields()["outcome"] == "review_hidden"
    assert PUBLIC_DISCOVERY_ACCEPT_CONFIDENCE == 70
