import unittest

from app.automation.discovery.contracts import DiscoveryProvider, NormalizedOpportunity
from app.services.source_research_service import SourceResearchService


class DiscoveryRoleSourceSeparationTests(unittest.TestCase):
    def test_role_search_does_not_accept_source_cards(self):
        source_card = NormalizedOpportunity(
            role="Breakdown Source",
            project="Playbill Jobs",
            union="Unknown",
            location="Online",
            description="Public jobs index.",
            original_post_url="https://playbill.com/jobs",
            audition_type="Unknown",
            audition_travel_hours=None,
            result_type="source",
        )

        self.assertFalse(DiscoveryProvider().validate(source_card))

    def test_role_search_accepts_specific_breakdown_cards(self):
        role_card = NormalizedOpportunity(
            role="Attorney",
            project="Streaming Drama",
            union="SAG-AFTRA",
            location="Philadelphia, PA",
            description="Specific active acting role seeking performers.",
            original_post_url="https://example.com/casting/attorney-role",
            audition_type="Self-Tape",
            audition_travel_hours=None,
            result_type="breakdown",
        )

        self.assertTrue(DiscoveryProvider().validate(role_card))

    def test_source_search_rejects_individual_role_urls(self):
        service = SourceResearchService(db=None)

        self.assertTrue(
            service._looks_like_individual_breakdown(
                {
                    "name": "Specific Playbill Role",
                    "source_url": "https://playbill.com/job/specific-role/abc123",
                    "base_url": "https://playbill.com",
                }
            )
        )

    def test_film_tv_source_search_returns_source_candidates_not_role_cards(self):
        service = SourceResearchService(db=None)
        candidates = service._source_candidates("FilmTV")

        self.assertGreater(len(candidates), 0)
        self.assertTrue(
            any(
                "film" in " ".join(str(value or "") for value in candidate.values()).lower()
                or "tv" in " ".join(str(value or "") for value in candidate.values()).lower()
                for candidate in candidates
            )
        )
        self.assertFalse(any(service._looks_like_individual_breakdown(candidate) for candidate in candidates))
        self.assertFalse(
            service._looks_like_individual_breakdown(
                {
                    "name": "Playbill Jobs",
                    "source_url": "https://playbill.com/jobs",
                    "base_url": "https://playbill.com",
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
