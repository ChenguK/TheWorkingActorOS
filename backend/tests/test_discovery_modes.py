import unittest

from app.automation.discovery.contracts import NormalizedOpportunity
from app.automation.discovery.service import DiscoveryAutomationService
from app.db.models import DiscoveryProviderSettings


class DiscoveryModeTests(unittest.TestCase):
    def test_film_tv_mode_excludes_theater_only_breakdown(self):
        item = NormalizedOpportunity(
            role="Esperança",
            project="Triangulo",
            union="Unknown",
            location="New York, NY",
            description="World premiere musical theater stage production with Latin-pop vocalist requirements.",
            original_post_url="https://playbill.com/job/example",
            audition_type="Unknown",
            audition_travel_hours=None,
            category="Theatre / Public Casting",
            production_details={"project_type": "Theater / Musical Theater"},
        )

        service = DiscoveryAutomationService(db=None)

        self.assertFalse(service._matches_mode(item, "FilmTV"))
        self.assertTrue(service._matches_mode(item, "Theater"))

    def test_theater_mode_excludes_film_tv_breakdown(self):
        item = NormalizedOpportunity(
            role="Detective",
            project="Streaming Crime Series",
            union="SAG-AFTRA",
            location="New York, NY",
            description="Episodic television series seeking actors for a recurring detective role.",
            original_post_url="https://example.com/breakdown",
            audition_type="Self-Tape",
            audition_travel_hours=None,
            category="Television",
            production_details={"project_type": "Television"},
        )

        service = DiscoveryAutomationService(db=None)

        self.assertTrue(service._matches_mode(item, "FilmTV"))
        self.assertFalse(service._matches_mode(item, "Theater"))

    def test_non_acting_listing_is_discarded_not_hidden(self):
        item = NormalizedOpportunity(
            role="Casting Coordinator",
            project="Regional Theater",
            union="Unknown",
            location="New York, NY",
            description="Hiring a casting coordinator for an administrative staff position.",
            original_post_url="https://example.com/job",
            audition_type="Unknown",
            audition_travel_hours=None,
            breakdown_classification="Non-Acting Job",
            rejection_reason="This is casting department employment, not an acting breakdown.",
        )
        visibility, _, rule, _ = DiscoveryAutomationService(db=None)._visibility(item)

        self.assertEqual(visibility, "discarded")
        self.assertEqual(rule, "breakdown_classification_rejected")

    def test_in_person_travel_miss_is_travel_exception(self):
        item = NormalizedOpportunity(
            role="Attorney",
            project="Streaming Drama",
            union="SAG-AFTRA",
            location="New York, NY",
            description="Seeking actors for an in-person audition.",
            original_post_url="https://example.com/breakdown",
            audition_type="In-Person",
            audition_travel_hours=3,
            breakdown_classification="Acting Role",
        )
        visibility, _, rule, _ = DiscoveryAutomationService(db=None)._visibility(item)

        self.assertEqual(visibility, "travel_exception")
        self.assertEqual(rule, "travel_exception")

    def test_default_search_intent_does_not_require_stretch_archetype(self):
        item = NormalizedOpportunity(
            role="Principal",
            project="Streaming Family Drama",
            union="SAG-AFTRA",
            location="Philadelphia, PA",
            description="Seeking a warm professional woman for a supporting role.",
            original_post_url="https://example.com/breakdown",
            audition_type="Self-Tape",
            audition_travel_hours=None,
            category="Television",
            production_details={"project_type": "Television"},
        )

        service = DiscoveryAutomationService(db=None)

        self.assertTrue(
            service._matches_search_intent(
                item,
                service._search_modes(None),
            )
        )

    def test_specific_archetype_search_requires_explicit_archetype_match(self):
        detective_item = NormalizedOpportunity(
            role="Detective Morris",
            project="Streaming Crime Series",
            union="SAG-AFTRA",
            location="New York, NY",
            description="Seeking a detective for a procedural television episode.",
            original_post_url="https://example.com/detective",
            audition_type="Self-Tape",
            audition_travel_hours=None,
            category="Television",
            production_details={"project_type": "Television"},
        )
        nurse_item = NormalizedOpportunity(
            role="Nurse",
            project="Medical Drama",
            union="SAG-AFTRA",
            location="Philadelphia, PA",
            description="Seeking a nurse for an episodic television scene.",
            original_post_url="https://example.com/nurse",
            audition_type="Self-Tape",
            audition_travel_hours=None,
            category="Television",
            production_details={"project_type": "Television"},
        )

        service = DiscoveryAutomationService(db=None)
        modes = service._search_modes(["Search Specific Archetype"])

        self.assertTrue(service._matches_search_intent(detective_item, modes, "Detective"))
        self.assertFalse(service._matches_search_intent(nurse_item, modes, "Detective"))

    def test_stretch_role_search_is_explicitly_restrictive(self):
        detective_item = NormalizedOpportunity(
            role="Detective",
            project="Streaming Crime Series",
            union="SAG-AFTRA",
            location="New York, NY",
            description="Seeking a detective for a procedural television episode.",
            original_post_url="https://example.com/detective",
            audition_type="Self-Tape",
            audition_travel_hours=None,
            category="Television",
            production_details={"project_type": "Television"},
        )
        parent_item = NormalizedOpportunity(
            role="Warm Parent",
            project="Family Drama",
            union="SAG-AFTRA",
            location="Philadelphia, PA",
            description="Seeking a supportive parent for a streaming drama.",
            original_post_url="https://example.com/parent",
            audition_type="Self-Tape",
            audition_travel_hours=None,
            category="Television",
            production_details={"project_type": "Television"},
        )

        service = DiscoveryAutomationService(db=None)
        service._active_stretch_terms = lambda: {"detective", "attorney"}
        modes = service._search_modes(["Find Stretch Roles"])

        self.assertTrue(service._matches_search_intent(detective_item, modes))
        self.assertFalse(service._matches_search_intent(parent_item, modes))

    def test_discovery_run_with_one_active_source_reports_very_limited_coverage(self):
        class FakeDb:
            def __init__(self):
                self.calls = 0

            def scalars(self, _statement):
                self.calls += 1
                if self.calls == 1:
                    return [
                        DiscoveryProviderSettings(
                            provider_key="indie_film_board",
                            display_name="Indie Film Casting Board",
                            tier=2,
                            category="Public Casting Sites",
                            source_type="public_breakdowns",
                            enabled=True,
                            provider_metadata={},
                            notes="Independent film and television casting page.",
                        )
                    ]
                return []

        class FakePlugin:
            implementation_key = "indie_film_board"
            name = "Indie Film Casting Board"

        coverage = DiscoveryAutomationService(FakeDb())._coverage_report("FilmTV", [FakePlugin()])

        self.assertEqual(coverage["approved_active_sources_checked"], 1)
        self.assertEqual(coverage["approved_mode_sources_available"], 1)
        self.assertEqual(coverage["coverage_level"], "Very Limited")
        self.assertIn("did not search the full public web", coverage["scope_note"])

    def test_discovery_run_with_zero_active_sources_reports_setup_guidance_data(self):
        class FakeDb:
            def __init__(self):
                self.calls = 0

            def scalars(self, _statement):
                self.calls += 1
                if self.calls == 1:
                    return [
                        DiscoveryProviderSettings(
                            provider_key="disabled_film_board",
                            display_name="Disabled Film Board",
                            tier=2,
                            category="Public Casting Sites",
                            source_type="public_breakdowns",
                            enabled=False,
                            provider_metadata={},
                            notes="Film and television casting page.",
                        )
                    ]
                return []

        coverage = DiscoveryAutomationService(FakeDb())._coverage_report("FilmTV", [])

        self.assertEqual(coverage["approved_active_sources_checked"], 0)
        self.assertEqual(coverage["approved_mode_sources_available"], 0)
        self.assertEqual(coverage["coverage_level"], "Very Limited")
        self.assertEqual(coverage["eligible_sources_skipped"], 1)
        self.assertEqual(coverage["skipped_source_reasons"][0]["reason"], "Disabled or paused.")

    def test_discovery_report_summarizes_public_web_candidates(self):
        service = DiscoveryAutomationService(db=None)
        report = service._discovery_report(
            [{"source": "Approved Source", "total_found": 2}],
            {
                "search_queries": ["query one", "query two"],
                "candidate_pages_found": 3,
                "candidate_pages_fetched": 3,
                "candidate_pages_parsed": 2,
                "candidate_reports": [
                    {"page_title": "Accepted Role", "url": "https://example.com/a", "source": "Parallel", "decision": "Accepted", "rejection_reason": None, "parser_confidence": 82},
                    {"page_title": "Expired Role", "url": "https://example.com/b", "source": "Parallel", "decision": "Rejected", "rejection_reason": "Expired", "parser_confidence": 70},
                    {"page_title": "Crew Job", "url": "https://example.com/c", "source": "Parallel", "decision": "Rejected", "rejection_reason": "Crew/Staff"},
                ],
            },
        )

        self.assertEqual(report["parallel_queries_run"], 2)
        self.assertEqual(report["candidate_pages_returned"], 3)
        self.assertEqual(report["accepted"], 1)
        self.assertEqual(report["rejected"], 2)
        self.assertEqual(report["top_rejection_reasons"]["Expired"], 1)
        self.assertEqual(report["approved_source_hits"], 2)
        self.assertEqual(report["public_web_hits"], 3)
        self.assertEqual(report["average_parser_confidence"], 76)


if __name__ == "__main__":
    unittest.main()
