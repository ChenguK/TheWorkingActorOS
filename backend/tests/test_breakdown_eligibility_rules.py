import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from app.db.models import ActorProfile, Opportunity, TravelEstimate
from app.services.opportunity_intelligence_service import (
    DEFAULT_EXCLUDED_ROLE_TYPES,
    DEFAULT_INCLUDED_ROLE_TYPES,
    OpportunityIntelligenceService,
)
from app.services.travel_service import TravelService


class BreakdownEligibilityRuleTests(unittest.TestCase):
    def setUp(self):
        self.travel_settings = SimpleNamespace(
            travel_provider="manual",
            google_maps_api_key=None,
            mapbox_access_token=None,
            openrouteservice_api_key=None,
            travel_cache_days=30,
        )
        self.settings_patch = patch(
            "app.services.travel_service.get_settings",
            return_value=self.travel_settings,
        )
        self.settings_patch.start()
        self.addCleanup(self.settings_patch.stop)

    def actor(self) -> ActorProfile:
        return ActorProfile(
            name="Actor",
            sag_status="SAG-AFTRA",
            union_status="SAG-AFTRA",
            current_location="Philadelphia, PA",
            playable_age_min=25,
            playable_age_max=35,
            gender_identities=["Woman"],
            gender_expression="Female Presenting",
            ethnicities=["African American"],
            racial_identities=["Black"],
            nationalities=[],
            languages=[],
            accents=[],
            disability_identities=[],
            skills=[],
            included_role_types=DEFAULT_INCLUDED_ROLE_TYPES,
            excluded_role_types=DEFAULT_EXCLUDED_ROLE_TYPES,
        )

    def opportunity(self, **overrides) -> Opportunity:
        data = {
            "role": "Role",
            "project": "Project",
            "project_type": "Television",
            "role_type": "Guest Star",
            "union": "SAG-AFTRA",
            "location": "New York, NY",
            "description": "Seeking Black female presenting performer, age 25-35.",
            "breakdown_classification": "Acting Role",
            "audition_type": "Self-Tape",
            "demographic_match_status": "Match",
            "source_metadata": {},
            "production_details": {},
            "role_details": {},
        }
        data.update(overrides)
        return Opportunity(**data)

    def test_excluded_role_type_is_discarded(self):
        opportunity = self.opportunity(role_type="Background")
        OpportunityIntelligenceService(db=None).apply_hard_eligibility(opportunity, self.actor())
        self.assertEqual(opportunity.visibility_status, "discarded")
        self.assertEqual(opportunity.hidden_by_rule, "dealbreaker_role_type")

    def test_demographic_mismatch_is_discarded(self):
        opportunity = self.opportunity(demographic_match_status="Not a Match")
        OpportunityIntelligenceService(db=None).apply_hard_eligibility(opportunity, self.actor())
        self.assertEqual(opportunity.visibility_status, "discarded")
        self.assertEqual(opportunity.hidden_by_rule, "dealbreaker_demographic_mismatch")

    def test_self_tape_does_not_apply_travel_rule(self):
        opportunity = self.opportunity(audition_type="Self-Tape", audition_drive_time=8)
        OpportunityIntelligenceService(db=None).apply_hard_eligibility(opportunity, self.actor())
        self.assertNotEqual(opportunity.visibility_status, "hidden")

    def test_nyc_in_person_nonlocal_uses_audition_location_for_travel_exception(self):
        opportunity = self.opportunity(
            audition_type="In-Person",
            audition_location="Ripley-Grier Studios, New York, NY",
            audition_travel_hours=2.3,
            audition_drive_time=None,
        )
        OpportunityIntelligenceService(db=None).apply_hard_eligibility(opportunity, self.actor())
        self.assertEqual(opportunity.visibility_status, "travel_exception")
        self.assertEqual(opportunity.hidden_by_rule, "travel_exception")
        self.assertIn("Audition location:", opportunity.hidden_reason)
        self.assertIn("Threshold:", opportunity.hidden_reason)

    def test_in_person_without_audition_location_needs_info_not_shoot_location_guess(self):
        opportunity = self.opportunity(
            audition_type="In-Person",
            audition_location=None,
            shoot_location="New York, NY",
            location="New York, NY",
            audition_travel_hours=None,
            audition_drive_time=None,
        )

        OpportunityIntelligenceService(db=None).apply_hard_eligibility(opportunity, self.actor())

        self.assertEqual(opportunity.visibility_status, "hidden")
        self.assertEqual(opportunity.hidden_by_rule, "audition_location_needs_info")
        self.assertTrue(opportunity.manual_review_required)
        self.assertIn("will not guess from shoot or performance location", opportunity.hidden_reason)

    def test_in_person_with_location_but_no_provider_or_manual_estimate_needs_info(self):
        opportunity = self.opportunity(
            audition_type="In-Person",
            audition_location="Ripley-Grier Studios, New York, NY",
            audition_travel_hours=None,
            audition_drive_time=None,
        )

        OpportunityIntelligenceService(db=None).apply_hard_eligibility(opportunity, self.actor())

        self.assertEqual(opportunity.visibility_status, "hidden")
        self.assertEqual(opportunity.hidden_by_rule, "audition_location_needs_info")
        self.assertIn("user-entered estimate", opportunity.hidden_reason)

    def test_self_tape_audition_travel_is_zero(self):
        opportunity = self.opportunity(
            audition_type="Self-Tape",
            audition_travel_hours=8,
            audition_drive_time=8,
        )

        OpportunityIntelligenceService(db=None).apply_audition_visibility(opportunity)

        self.assertEqual(opportunity.audition_drive_time, 0)
        self.assertEqual(opportunity.audition_travel_hours, 0)
        self.assertEqual(opportunity.visibility_status, "visible")

    def test_virtual_audition_travel_is_zero(self):
        opportunity = self.opportunity(
            audition_type="Virtual",
            audition_travel_hours=5,
            audition_drive_time=5,
        )

        OpportunityIntelligenceService(db=None).apply_audition_visibility(opportunity)

        self.assertEqual(opportunity.audition_drive_time, 0)
        self.assertEqual(opportunity.audition_travel_hours, 0)
        self.assertEqual(opportunity.visibility_status, "visible")

    def test_in_person_under_threshold_is_visible(self):
        opportunity = self.opportunity(
            audition_type="In-Person",
            audition_location="Philadelphia, PA",
            audition_travel_hours=1.5,
            audition_drive_time=None,
        )

        OpportunityIntelligenceService(db=None).apply_hard_eligibility(opportunity, self.actor())

        self.assertEqual(opportunity.visibility_status, "visible")
        self.assertIsNone(opportunity.hidden_by_rule)

    def test_travel_service_manual_fallback_requires_user_entered_estimate(self):
        service = TravelService(db=None)

        missing = service.drive_time(
            origin_text="Philadelphia, PA",
            destination_text="New York, NY",
            manual_drive_hours=None,
        )
        manual = service.drive_time(
            origin_text="Philadelphia, PA",
            destination_text="New York, NY",
            manual_drive_hours=2.5,
        )

        self.assertIsNone(missing)
        self.assertIsNotNone(manual)
        self.assertEqual(manual.provider, "manual_override")
        self.assertEqual(manual.drive_hours, 2.5)
        self.assertEqual(manual.metadata["label"], "User-entered estimate")
        self.assertTrue(manual.is_manual_override)

    def test_cached_travel_result_is_reused(self):
        service = TravelService(db=None)
        now = datetime.now(timezone.utc)
        cached = TravelEstimate(
            origin_text="philadelphia, pa",
            destination_text="new york, ny",
            drive_minutes=90,
            drive_hours=1.5,
            distance_miles=95,
            provider="openrouteservice_directions",
            confidence_score=0.9,
            calculated_at=now,
            expires_at=now + timedelta(days=1),
        )
        service._cached = lambda _origin, _destination: cached
        service._provider_drive_time = lambda _origin, _destination: (_ for _ in ()).throw(AssertionError("provider should not be called"))

        result = service.drive_time(origin_text="Philadelphia, PA", destination_text="New York, NY")

        self.assertTrue(result.cached)
        self.assertEqual(result.drive_hours, 1.5)
        self.assertEqual(result.provider, "openrouteservice_directions")

    def test_missing_api_key_reports_not_configured(self):
        service = TravelService(db=None)
        original_provider = service.settings.travel_provider
        original_key = service.settings.openrouteservice_api_key
        try:
            service.settings.travel_provider = "openrouteservice"
            service.settings.openrouteservice_api_key = None
            status = service.provider_status()
        finally:
            service.settings.travel_provider = original_provider
            service.settings.openrouteservice_api_key = original_key

        self.assertEqual(status["state"], "Not Configured")
        self.assertFalse(status["configured"])

    def test_present_api_key_reports_openrouteservice_configured(self):
        self.travel_settings.travel_provider = "openrouteservice"
        self.travel_settings.openrouteservice_api_key = "test-openrouteservice-key"

        status = TravelService(db=None).provider_status()

        self.assertEqual(status["provider"], "openrouteservice")
        self.assertEqual(status["state"], "Configured")
        self.assertTrue(status["configured"])


if __name__ == "__main__":
    unittest.main()
