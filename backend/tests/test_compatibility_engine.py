import unittest

from app.db.models import ActorProfile, Opportunity
from app.services.compatibility_engine import CompatibilityEngine
from app.services.demographic_match_service import DemographicMatchService


class CompatibilityEngineTests(unittest.TestCase):
    def actor(self) -> ActorProfile:
        return ActorProfile(
            name="Actor",
            sag_status="SAG-AFTRA",
            union_status="SAG-AFTRA",
            current_location="Philadelphia, PA",
            playable_age_min=25,
            playable_age_max=35,
            secondary_playable_age_min=30,
            secondary_playable_age_max=40,
            skills=[],
            gender_identities=["Woman"],
            gender_expression="Female Presenting",
            ethnicities=["African American"],
            racial_identities=["Black"],
            nationalities=[],
            languages=[],
            accents=[],
            disability_identities=[],
        )

    def test_boundary_age_overlap_is_comfortable_stretch_not_direct_match(self) -> None:
        decision = CompatibilityEngine().age_compatibility(
            actor_ranges=[(25, 35), (30, 40)],
            role_ranges=[(40, 60)],
        )

        self.assertEqual(decision.label, "Comfortable Stretch")
        self.assertEqual(decision.hard_status, "Match")
        self.assertIn("not a perfect match", decision.explanation)

    def test_demographic_service_stores_compatibility_label(self) -> None:
        opportunity = Opportunity(
            role="Attorney",
            project="Series",
            project_type="Television",
            union="SAG-AFTRA",
            location="New York, NY",
            description="Co-Star / 40-60 / Woman / Any Ethnic Appearance",
        )

        DemographicMatchService(db=None).apply(opportunity, self.actor())

        age_check = next(
            check for check in opportunity.demographic_match_details["checks"] if check["label"] == "Playable Age"
        )
        self.assertEqual(age_check["compatibility_label"], "Comfortable Stretch")
        self.assertEqual(opportunity.demographic_match_details["compatibility_label"], "Comfortable Stretch")


if __name__ == "__main__":
    unittest.main()
