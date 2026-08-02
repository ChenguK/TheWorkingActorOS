import unittest
from pathlib import Path
from types import SimpleNamespace

from app.automation.discovery.public_web_search import PublicWebBreakdownSearch
from app.automation.discovery.public_web_search import (
    PARALLEL_ADVANCED_SETTINGS,
    PUBLIC_WEB_MAX_ARCHETYPE_TERMS,
    PUBLIC_WEB_MAX_LANGUAGE_TERMS,
    PUBLIC_WEB_MAX_LOCATION_TERMS,
    PUBLIC_WEB_MAX_QUERY_COUNT,
    PUBLIC_WEB_MAX_QUERY_LENGTH,
)


class FakeActor:
    name = "Fixture Actor"
    email = "fixture@example.test"
    phone = "212-555-0199"
    playable_age_min = 25
    playable_age_max = 35
    secondary_playable_age_min = 36
    secondary_playable_age_max = 40
    languages = ["English"]
    gender_identities = ["Woman"]
    racial_identities = ["Black / African American"]
    ethnicities = []
    union_status = "SAG-AFTRA"
    sag_status = "SAG-AFTRA"
    current_location = "New York, NY"
    included_role_types = ["Lead", "Supporting", "Crew"]
    excluded_role_types = ["Crew", "Staff Job"]
    skills = ["Comedy", "Warm Authority"]
    notes = "PRIVATE-NOTES-SENTINEL"
    travel_preferences = [
        SimpleNamespace(
            working_as_local_drive_time=180,
            flight_allowed=True,
            international_allowed=False,
            audition_self_tape_allowed=True,
            audition_virtual_allowed=True,
            working_notes="PRIVATE-TRAVEL-NOTES-SENTINEL",
        )
    ]
    assets = [
        SimpleNamespace(
            archetype_names=["Warm Authority", "Detective"],
            original_filename="PRIVATE-ASSET-FILENAME-SENTINEL.jpg",
            local_file_path="/private/PRIVATE-ASSET-PATH-SENTINEL.jpg",
            description="PRIVATE-ASSET-DESCRIPTION-SENTINEL",
        )
    ]


class FakeParallelClient:
    def __init__(self):
        self.calls = []

    def search(self, **_kwargs):
        self.calls.append(_kwargs)
        return {
            "results": [
                {"url": "https://casting.example.com/roles/feature-supporting"},
                {"link": "https://casting.example.com/roles/feature-supporting#details"},
            ]
        }


class PublicWebBreakdownSearchTests(unittest.TestCase):
    def configured_service(self, actor=None, client=None):
        service = PublicWebBreakdownSearch(
            actor if actor is not None else FakeActor(),
            parallel_client=client or FakeParallelClient(),
        )
        service.configured = lambda: True
        return service

    def actor(self, **overrides):
        values = {
            name: getattr(FakeActor, name)
            for name in (
                "name",
                "email",
                "phone",
                "playable_age_min",
                "playable_age_max",
                "secondary_playable_age_min",
                "secondary_playable_age_max",
                "languages",
                "gender_identities",
                "racial_identities",
                "ethnicities",
                "union_status",
                "sag_status",
                "current_location",
                "included_role_types",
                "excluded_role_types",
                "skills",
                "notes",
                "travel_preferences",
                "assets",
            )
        }
        values.update(overrides)
        return SimpleNamespace(**values)

    def test_complete_profile_generates_deterministic_bounded_queries(self):
        service = PublicWebBreakdownSearch(FakeActor(), parallel_client=FakeParallelClient())
        service.configured = lambda: True

        first = service.search_queries()
        second = service.search_queries()

        self.assertEqual(first, second)
        self.assertEqual(len(first), PUBLIC_WEB_MAX_QUERY_COUNT)
        joined = " ".join(first)
        self.assertIn("playable age 25-35 or 36-40", joined)
        self.assertIn("Woman", joined)
        self.assertIn("Black / African American", joined)
        self.assertIn("SAG-AFTRA", joined)
        self.assertIn("English language roles", joined)
        self.assertIn("New York, NY", joined)
        self.assertIn("working as local within 180 minutes", joined)
        self.assertIn("approved travel", joined)
        self.assertIn("Warm Authority Detective roles", joined)
        self.assertIn("self tape remote audition", joined)
        self.assertNotIn("Crew", joined)

    def test_incomplete_profile_omits_missing_dimensions_without_defaults(self):
        actor = self.actor(
            playable_age_min=None,
            playable_age_max=None,
            secondary_playable_age_min=None,
            secondary_playable_age_max=None,
            languages=[],
            gender_identities=[],
            racial_identities=[],
            ethnicities=[],
            union_status="Unknown",
            sag_status="Unknown",
            current_location="",
            included_role_types=[],
            travel_preferences=[],
            assets=[],
        )

        queries = self.configured_service(actor).search_queries()
        joined = " ".join(queries).lower()

        self.assertTrue(queries)
        for fabricated in (
            "english",
            "woman",
            "female",
            "man",
            "male",
            "sag-aftra",
            "25-40",
            "open ethnicity",
        ):
            self.assertNotIn(fabricated, joined)

    def test_gender_identity_and_open_gender_behavior(self):
        cases = [
            (["Nonbinary"], "Nonbinary", ["woman", "gender open"]),
            (["Woman", "Nonbinary"], "Woman Nonbinary", ["gender open"]),
            (["Any Gender", "Woman"], "gender open", ["Any Gender", "Woman"]),
            ([], None, ["woman", "female", "man", "male", "gender open"]),
        ]
        for identities, expected, absent in cases:
            with self.subTest(identities=identities):
                queries = self.configured_service(
                    self.actor(gender_identities=identities)
                ).search_queries()
                fit = queries[0]
                if expected:
                    self.assertIn(expected, fit)
                for term in absent:
                    self.assertNotIn(term, fit)

    def test_playable_age_variants(self):
        cases = [
            ((25, 35, None, None), "playable age 25-35"),
            ((30, 30, None, None), "playable age 30"),
            ((25, 35, 40, 42), "playable age 25-35 or 40-42"),
            ((None, 35, None, None), None),
            ((40, 35, None, None), None),
            ((25, 35, 45, 40), "playable age 25-35"),
        ]
        for ages, expected in cases:
            with self.subTest(ages=ages):
                actor = self.actor(
                    playable_age_min=ages[0],
                    playable_age_max=ages[1],
                    secondary_playable_age_min=ages[2],
                    secondary_playable_age_max=ages[3],
                )
                fit = self.configured_service(actor).search_queries()[0]
                if expected:
                    self.assertIn(expected, fit)
                else:
                    self.assertNotIn("playable age", fit)

    def test_identity_terms_are_optional_deduplicated_and_bounded(self):
        cases = [
            (["Latine"], [], ["Latine"]),
            (["Black", "Latine"], ["Afro-Latine"], ["Black", "Latine", "Afro-Latine"]),
            ([], [], []),
            (["One", "Two", "Three", "Four"], ["Five"], ["One", "Two", "Three"]),
            (["Latine", "latine"], [], ["Latine"]),
        ]
        for racial, ethnicities, expected in cases:
            with self.subTest(racial=racial, ethnicities=ethnicities):
                fit = self.configured_service(
                    self.actor(racial_identities=racial, ethnicities=ethnicities)
                ).search_queries()[0]
                for term in expected:
                    self.assertIn(term, fit)
                self.assertNotIn("Four", fit)
                self.assertNotIn("Five", fit)

    def test_union_status_variants(self):
        cases = [
            ("SAG-AFTRA", "SAG-AFTRA"),
            ("Non-Union", "non-union"),
            ("Union and Non-Union", "union and non-union"),
            ("Both", "union and non-union"),
            ("SAG Eligible", "SAG Eligible"),
            ("AEA", "AEA"),
            ("ACTRA", "ACTRA"),
            ("Unknown", None),
        ]
        for status, expected in cases:
            with self.subTest(status=status):
                queries = self.configured_service(
                    self.actor(union_status=status, sag_status="Unknown")
                ).search_queries()
                union_queries = [query for query in queries if "language roles" not in query]
                joined = " ".join(union_queries)
                if expected:
                    self.assertIn(expected, joined)
                else:
                    self.assertNotIn("SAG", joined)
                    self.assertNotIn("non-union", joined)

    def test_languages_are_not_defaulted_and_are_bounded(self):
        cases = [
            (["English"], ["English"]),
            (["Spanish"], ["Spanish"]),
            (["Spanish", "French", "ASL"], ["Spanish", "French", "ASL"]),
            ([], []),
            (["One", "Two", "Three", "Four"], ["One", "Two", "Three"]),
        ]
        for languages, expected in cases:
            with self.subTest(languages=languages):
                queries = self.configured_service(self.actor(languages=languages)).search_queries()
                language_queries = [query for query in queries if "language roles" in query]
                self.assertEqual(bool(language_queries), bool(expected))
                if language_queries:
                    query = language_queries[0]
                    for term in expected:
                        self.assertIn(term, query)
                    self.assertNotIn("Four", query)
                    self.assertLessEqual(len(expected), PUBLIC_WEB_MAX_LANGUAGE_TERMS)

    def test_location_travel_and_remote_scope(self):
        cases = [
            ("Atlanta, GA", [], ["Atlanta, GA"], []),
            (
                "Atlanta, GA",
                [
                    SimpleNamespace(
                        working_as_local_drive_time=120,
                        flight_allowed=False,
                        international_allowed=False,
                        audition_self_tape_allowed=False,
                        audition_virtual_allowed=False,
                    )
                ],
                ["Atlanta, GA", "working as local within 120 minutes"],
                [],
            ),
            (
                "Atlanta, GA",
                [
                    SimpleNamespace(
                        working_as_local_drive_time=120,
                        flight_allowed=True,
                        international_allowed=False,
                        audition_self_tape_allowed=True,
                        audition_virtual_allowed=True,
                    )
                ],
                ["Atlanta, GA", "approved travel"],
                ["self tape", "remote audition"],
            ),
            ("", [], [], []),
        ]
        for location, preferences, location_expected, remote_expected in cases:
            with self.subTest(location=location, preferences=bool(preferences)):
                queries = self.configured_service(
                    self.actor(current_location=location, travel_preferences=preferences)
                ).search_queries()
                joined = " ".join(queries)
                for term in location_expected + remote_expected:
                    self.assertIn(term, joined)
                self.assertLessEqual(
                    len(
                        self.configured_service(
                            self.actor(current_location=location, travel_preferences=preferences)
                        )._location_terms(
                            self.actor(current_location=location, travel_preferences=preferences)
                        )
                    ),
                    PUBLIC_WEB_MAX_LOCATION_TERMS,
                )

    def test_role_preferences_only_add_supported_film_tv_acting_roles(self):
        actor = self.actor(
            included_role_types=[
                "Lead",
                "Supporting",
                "Principal",
                "Crew",
                "Staff Job",
                "Theater Principal",
            ],
            excluded_role_types=["Crew", "Staff Job", "Production Assistant"],
        )

        joined = " ".join(self.configured_service(actor).search_queries())

        self.assertIn("Lead Supporting Principal", joined)
        for excluded in ("Crew", "Staff Job", "Production Assistant", "Theater Principal"):
            self.assertNotIn(excluded, joined)

    def test_archetypes_are_optional_deduplicated_and_bounded(self):
        cases = [
            ([], []),
            (["Detective"], ["Detective"]),
            (
                ["Detective", "detective", "Doctor", "Parent", "Executive"],
                ["Detective", "Doctor", "Parent"],
            ),
        ]
        for archetypes, expected in cases:
            with self.subTest(archetypes=archetypes):
                assets = [SimpleNamespace(archetype_names=archetypes)] if archetypes else []
                queries = self.configured_service(self.actor(assets=assets)).search_queries()
                archetype_queries = [
                    query
                    for query in queries
                    if query.endswith(" roles")
                    and "language roles" not in query
                    and "open casting" not in query
                ]
                self.assertEqual(bool(archetype_queries), bool(expected))
                if archetype_queries:
                    for term in expected:
                        self.assertIn(term, archetype_queries[0])
                    self.assertNotIn("Executive", archetype_queries[0])
                    self.assertLessEqual(len(expected), PUBLIC_WEB_MAX_ARCHETYPE_TERMS)

    def test_global_query_bounds_deduplication_and_no_combinatorial_expansion(self):
        repeated = ["Same"] * 20
        actor = self.actor(
            languages=repeated,
            gender_identities=repeated,
            racial_identities=repeated,
            ethnicities=repeated,
            included_role_types=["Lead"] * 20,
            assets=[SimpleNamespace(archetype_names=repeated)],
        )

        first = self.configured_service(actor).search_queries()
        second = self.configured_service(actor).search_queries()

        self.assertEqual(first, second)
        self.assertLessEqual(len(first), PUBLIC_WEB_MAX_QUERY_COUNT)
        self.assertEqual(len(first), len({query.casefold() for query in first}))
        self.assertTrue(all(query.strip() for query in first))
        self.assertTrue(all(len(query) <= PUBLIC_WEB_MAX_QUERY_LENGTH for query in first))

    def test_provider_disabled_and_portfolio_demo_generate_no_queries_or_calls(self):
        for portfolio_demo in (False, True):
            with self.subTest(portfolio_demo=portfolio_demo):
                client = FakeParallelClient()
                service = PublicWebBreakdownSearch(FakeActor(), parallel_client=client)
                service.settings = SimpleNamespace(
                    is_portfolio_demo=portfolio_demo,
                    web_search_provider="parallel" if portfolio_demo else "none",
                    parallel_api_key="fixture-key" if portfolio_demo else None,
                )

                self.assertEqual(service.search_queries(), [])
                result = service.search("FilmTV")

                self.assertFalse(result.run)
                self.assertEqual(client.calls, [])

    def test_parallel_call_and_result_budgets_are_unchanged(self):
        client = FakeParallelClient()
        service = self.configured_service(client=client)
        service._fetch_visible_text = lambda _url: None

        service.search("FilmTV")

        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.calls[0]["advanced_settings"], {"max_results": 10})
        self.assertEqual(PARALLEL_ADVANCED_SETTINGS, {"max_results": 10})
        self.assertLessEqual(len(client.calls[0]["search_queries"]), PUBLIC_WEB_MAX_QUERY_COUNT)

    def test_private_profile_and_asset_fields_never_enter_queries(self):
        actor = self.actor(
            name="PRIVATE-NAME-SENTINEL",
            email="PRIVATE-EMAIL-SENTINEL@example.test",
            phone="212-555-0111",
            street_address="99 PRIVATE-STREET-SENTINEL Road",
            notes="PRIVATE-NOTES-SENTINEL",
            current_location="99 PRIVATE-STREET-SENTINEL Road, New York, NY 10001",
            assets=[
                SimpleNamespace(
                    archetype_names=["Detective"],
                    original_filename="PRIVATE-ASSET-FILENAME-SENTINEL.jpg",
                    local_file_path="/private/PRIVATE-ASSET-PATH-SENTINEL.jpg",
                    description="PRIVATE-ASSET-DESCRIPTION-SENTINEL",
                )
            ],
        )

        joined = " ".join(self.configured_service(actor).search_queries())

        for sentinel in (
            "PRIVATE-NAME-SENTINEL",
            "PRIVATE-EMAIL-SENTINEL",
            "212-555-0111",
            "PRIVATE-STREET-SENTINEL",
            "PRIVATE-NOTES-SENTINEL",
            "PRIVATE-ASSET-FILENAME-SENTINEL",
            "PRIVATE-ASSET-PATH-SENTINEL",
            "PRIVATE-ASSET-DESCRIPTION-SENTINEL",
        ):
            self.assertNotIn(sentinel, joined)

    def test_parallel_response_urls_are_deduplicated_without_fragments(self):
        service = PublicWebBreakdownSearch(FakeActor(), parallel_client=FakeParallelClient())

        urls = service._extract_urls(FakeParallelClient().search())

        self.assertEqual(urls, ["https://casting.example.com/roles/feature-supporting"])

    def test_current_duplicate_result_contract_keeps_only_url_and_title(self):
        service = PublicWebBreakdownSearch(FakeActor(), parallel_client=FakeParallelClient())
        response = {
            "results": [
                {
                    "url": "https://casting.example.com/roles/feature-supporting#details",
                    "title": "Feature Supporting Role",
                    "excerpt": "Provider evidence that is not retained.",
                    "id": "provider-result-1",
                },
                {
                    "link": "https://casting.example.com/roles/feature-supporting",
                    "title": "Duplicate title is discarded with the duplicate URL.",
                },
            ]
        }

        records = service._extract_candidate_records(response)

        self.assertEqual(
            records,
            [
                {
                    "url": "https://casting.example.com/roles/feature-supporting",
                    "page_title": "Feature Supporting Role",
                }
            ],
        )
        self.assertNotIn("excerpt", records[0])
        self.assertNotIn("id", records[0])

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

    def test_current_ambiguous_casting_article_is_parsed_as_an_acting_role(self):
        service = PublicWebBreakdownSearch(FakeActor(), parallel_client=FakeParallelClient())
        page_text = (
            "Industry article: Casting directors discuss how actors prepare for feature film auditions. "
            "The article mentions a lead role, supporting role, self tape, and SAG-AFTRA casting calls, "
            "but it provides no actionable role or submission deadline."
        )

        item = service._normalize_candidate(
            "https://news.example.com/features/casting-advice", page_text
        )

        self.assertIsNotNone(item)
        self.assertEqual(item.breakdown_classification, "Theater Role")
        self.assertEqual(item.original_post_url, "https://news.example.com/features/casting-advice")
        self.assertEqual(item.source_metadata["source_url"], item.original_post_url)
        self.assertNotIn("provider_excerpt", item.source_metadata)

    def test_current_staff_or_crew_page_is_rejected_before_normalization(self):
        service = PublicWebBreakdownSearch(FakeActor(), parallel_client=FakeParallelClient())
        page_text = (
            "Production company hiring a casting coordinator and production assistant. "
            "This administrative staff job supports a film production office."
        )

        item = service._normalize_candidate(
            "https://jobs.example.com/casting-coordinator", page_text
        )

        self.assertIsNone(item)

    def test_mocked_parallel_response_with_urls_reports_candidate_pages(self):
        class ObjectParallelClient:
            def search(self, **_kwargs):
                return SimpleNamespace(
                    results=[
                        SimpleNamespace(
                            url="https://casting.example.com/roles/current-tv",
                            title="Current TV Role",
                        )
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
        source = (
            Path(__file__).resolve().parents[2]
            / "frontend/src/features/breakdowns/components/BreakdownDiscovery.tsx"
        ).read_text()

        self.assertIn("Public web search ran through Parallel", source)
        self.assertIn(
            "Public web search is not configured. Only approved sources were searched.", source
        )


if __name__ == "__main__":
    unittest.main()
