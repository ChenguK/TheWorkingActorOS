import unittest
from datetime import datetime, timezone

import pytest

from app.db.models import Opportunity
from app.services.trust_verification_service import TrustVerificationService


def opportunity(**overrides):
    values = {
        "role": "Attorney",
        "project": "Streaming Drama",
        "union": "SAG-AFTRA",
        "location": "New York, NY",
        "description": "Casting call seeking actors. Role: Attorney. Self-tape. Submit headshot and resume.",
        "original_post_url": "https://example.com/breakdown",
        "breakdown_classification": "Acting Role",
        "audition_type": "Self-Tape",
        "demographic_match_status": "Match",
        "source_metadata": {},
        "production_details": {},
        "role_details": {},
        "extracted_facts": {"role": "Attorney"},
        "ai_inference": {"likely_archetype": "Authority"},
    }
    values.update(overrides)
    return Opportunity(**values)


class TrustVerificationServiceTests(unittest.TestCase):
    def test_non_acting_listing_gets_plain_language_failure(self):
        item = opportunity(
            description="Casting Coordinator, Goodman Theatre. Full-time staff position with benefits.",
            breakdown_classification="Non-Acting Job",
            rejection_reason="This is an employment/job listing, not an acting breakdown.",
        )

        TrustVerificationService(db=None).verify(item)

        verification = item.source_metadata["trust_verification"]
        self.assertEqual(verification["status"], "Blocked")
        self.assertIn("employment/job listing", " ".join(verification["plain_language_reasons"]))

    def test_in_person_without_audition_location_needs_info(self):
        item = opportunity(audition_type="In-Person", audition_location=None)

        TrustVerificationService(db=None).verify(item)

        reasons = item.source_metadata["trust_verification"]["plain_language_reasons"]
        self.assertIn("Needs audition location before travel can be calculated.", reasons)

    def test_demo_data_is_blocked(self):
        item = opportunity(is_demo_data=True)

        TrustVerificationService(db=None).verify(item)

        self.assertEqual(item.source_metadata["trust_verification"]["status"], "Blocked")
        self.assertIn(
            "Demo data is hidden from real actor workflows.",
            item.source_metadata["trust_verification"]["plain_language_reasons"],
        )

    def test_protected_platform_requires_user_import_or_entry(self):
        item = opportunity(platform="Actors Access", source_type="Platform Discovery")

        TrustVerificationService(db=None).verify(item)

        reasons = item.source_metadata["trust_verification"]["plain_language_reasons"]
        self.assertIn(
            "Do not assume private platform data is available unless the actor manually enters or imports it.",
            reasons,
        )


def _date_check(item):
    return TrustVerificationService(db=None)._date_checks(item)[0]


@pytest.mark.parametrize(
    "overrides",
    [
        {"submission_deadline": datetime(2035, 12, 31, tzinfo=timezone.utc)},
        {"extracted_facts": {"dates": {"submission_deadline": "December 31, 2035"}}},
        {"role_details": {"submission_deadline": "December 31, 2035"}},
        {"production_details": {"submission_deadline": "December 31, 2035"}},
    ],
    ids=["scalar", "extracted-facts", "role-details", "production-details"],
)
def test_date_verification_accepts_every_supported_date_source(overrides):
    item = opportunity(**overrides)

    check = _date_check(item)

    assert check == {
        "name": "Date Verification",
        "status": "pass",
        "reason": "Dates are stored in separate submission, audition, callback, and work fields.",
    }


def test_structured_deadline_counts_when_scalar_columns_are_empty():
    item = opportunity(production_details={"submission_deadline": "December 31, 2035"})

    check = _date_check(item)

    assert item.submission_deadline is None
    assert item.audition_deadline is None
    assert item.callback_date is None
    assert check["status"] == "pass"


@pytest.mark.parametrize(
    "overrides",
    [
        {},
        {"role_details": {"submission_deadline": "early next week"}},
    ],
    ids=["missing", "malformed-structured"],
)
def test_date_verification_preserves_warning_without_a_usable_date(overrides):
    check = _date_check(opportunity(**overrides))

    assert check == {
        "name": "Date Verification",
        "status": "warning",
        "reason": "No submission, audition, callback, or work dates were found.",
    }


def test_expired_structured_deadline_is_date_evidence_not_a_missing_date():
    check = _date_check(opportunity(production_details={"submission_deadline": "January 1, 2020"}))

    assert check["status"] == "pass"
    assert "No submission" not in check["reason"]


if __name__ == "__main__":
    unittest.main()
