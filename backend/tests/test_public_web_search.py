import unittest
from pathlib import Path
from types import SimpleNamespace

from app.automation.discovery.public_web_search import PublicWebBreakdownSearch


class FakeActor:
    playable_age_min = 25
    playable_age_max = 35
    secondary_playable_age_max = 40
    languages = ["English"]
    racial_identities = ["Black / African American"]
    ethnicities = []
    skills = ["Comedy", "Warm Authority"]


class FakeParallelClient:
    def search(self, **_kwargs):
        return {
            "results": [
                {"url": "https://casting.example.com/roles/feature-supporting"},
                {"link": "https://casting.example.com/roles/feature-supporting#details"},
            ]
        }


class PublicWebBreakdownSearchTests(unittest.TestCase):
    def test_generates_profile_first_english_queries(self):
        service = PublicWebBreakdownSearch(FakeActor(), parallel_client=FakeParallelClient())

        queries = service.search_queries()

        self.assertTrue(any("Black African American" in query for query in queries))
        self.assertTrue(any("25-40" in query for query in queries))
        self.assertTrue(any("self tape" in query for query in queries))
        self.assertFalse(any("Detective" in query for query in queries[:5]))
        self.assertGreaterEqual(len(queries), 15)
        self.assertTrue(any("streaming" in query for query in queries))
        self.assertTrue(any("student film" in query for query in queries))
        self.assertTrue(any("open ethnicity" in query for query in queries))

    def test_parallel_response_urls_are_deduplicated_without_fragments(self):
        service = PublicWebBreakdownSearch(FakeActor(), parallel_client=FakeParallelClient())

        urls = service._extract_urls(FakeParallelClient().search())

        self.assertEqual(urls, ["https://casting.example.com/roles/feature-supporting"])

    def test_actual_parallel_response_shape_extracts_urls(self):
        service = PublicWebBreakdownSearch(FakeActor(), parallel_client=FakeParallelClient())
        response = SimpleNamespace(
            results=[
                SimpleNamespace(
                    url="https://casting.example.com/roles/current-feature#details",
                    title="Current Feature Role",
                    excerpts=["SAG-AFTRA self-tape role."],
                )
            ]
        )

        urls = service._extract_urls(response)

        self.assertEqual(urls, ["https://casting.example.com/roles/current-feature"])

    def test_search_returns_normalized_breakdown_from_verified_page(self):
        service = PublicWebBreakdownSearch(FakeActor(), parallel_client=FakeParallelClient())
        service.configured = lambda: True
        service._fetch_visible_text = lambda _url: (
            "Project: River City Feature\n"
            "Role: Principal Woman\n"
            "SAG-AFTRA feature film casting call seeking actors. "
            "Black woman 25-40. Self-tape submission instructions. "
            "Lead, supporting, and principal talent considered."
        )

        result = service.search("FilmTV")

        self.assertTrue(result.run)
        self.assertEqual(result.candidate_pages_found, 1)
        self.assertEqual(result.candidate_reports[0]["decision"], "Parsed")
        self.assertIsNone(result.candidate_reports[0]["rejection_reason"])
        self.assertEqual(len(result.normalized), 1)
        self.assertEqual(result.normalized[0].breakdown_classification, "Acting Role")
        self.assertEqual(result.normalized[0].audition_type, "Self-Tape")

    def test_mocked_parallel_response_with_urls_reports_candidate_pages(self):
        class ObjectParallelClient:
            def search(self, **_kwargs):
                return SimpleNamespace(
                    results=[
                        SimpleNamespace(url="https://casting.example.com/roles/current-tv", title="Current TV Role")
                    ]
                )

        service = PublicWebBreakdownSearch(FakeActor(), parallel_client=ObjectParallelClient())
        service.configured = lambda: True
        service._fetch_visible_text = lambda _url: (
            "Project: Current TV Drama\n"
            "Role: Co-Star Woman\n"
            "SAG-AFTRA television casting call seeking Black woman 25-40. "
            "Self tape instructions included."
        )

        result = service.search("FilmTV")

        self.assertEqual(result.candidate_pages_found, 1)
        self.assertEqual(len(result.normalized), 1)
        self.assertEqual(result.candidate_reports[0]["page_title"], "Current TV Role")

    def test_empty_parallel_response_reports_zero_candidates(self):
        class EmptyParallelClient:
            def search(self, **_kwargs):
                return SimpleNamespace(results=[])

        service = PublicWebBreakdownSearch(FakeActor(), parallel_client=EmptyParallelClient())
        service.configured = lambda: True

        result = service.search("FilmTV")

        self.assertTrue(result.run)
        self.assertEqual(result.candidate_pages_found, 0)
        self.assertEqual(result.candidates_rejected, 0)
        self.assertEqual(result.normalized, [])

    def test_malformed_parallel_response_does_not_crash(self):
        class MalformedParallelClient:
            def search(self, **_kwargs):
                return object()

        service = PublicWebBreakdownSearch(FakeActor(), parallel_client=MalformedParallelClient())
        service.configured = lambda: True

        result = service.search("FilmTV")

        self.assertTrue(result.run)
        self.assertEqual(result.candidate_pages_found, 0)
        self.assertEqual(result.normalized, [])

    def test_not_configured_is_honest(self):
        service = PublicWebBreakdownSearch(FakeActor(), parallel_client=FakeParallelClient())
        service.configured = lambda: False

        result = service.search("FilmTV")

        self.assertFalse(result.run)
        self.assertIn("not configured", result.reason.lower())

    def test_frontend_copy_distinguishes_parallel_run_state(self):
        source = (Path(__file__).resolve().parents[2] / "frontend/src/features/breakdowns/components/BreakdownDiscovery.tsx").read_text()

        self.assertIn("Public web search ran through Parallel", source)
        self.assertIn("Public web search is not configured. Only approved sources were searched.", source)


if __name__ == "__main__":
    unittest.main()
