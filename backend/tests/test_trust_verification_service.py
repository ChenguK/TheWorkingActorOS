import unittest

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
        self.assertIn("Demo data is hidden from real actor workflows.", item.source_metadata["trust_verification"]["plain_language_reasons"])

    def test_protected_platform_requires_user_import_or_entry(self):
        item = opportunity(platform="Actors Access", source_type="Platform Discovery")

        TrustVerificationService(db=None).verify(item)

        reasons = item.source_metadata["trust_verification"]["plain_language_reasons"]
        self.assertIn(
            "Do not assume private platform data is available unless the actor manually enters or imports it.",
            reasons,
        )


if __name__ == "__main__":
    unittest.main()
