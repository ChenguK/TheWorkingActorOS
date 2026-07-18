import unittest

from app.db.models import Opportunity, Submission
from app.services.intelligence_service import IntelligenceService


class CastingPatternsTests(unittest.TestCase):
    def service(self) -> IntelligenceService:
        return IntelligenceService(db=None)

    def test_casting_pattern_stages_are_based_on_actor_activity(self):
        service = self.service()

        self.assertEqual(service._casting_pattern_stage([Opportunity() for _ in range(4)], [])["stage"], "Add Data First")
        self.assertEqual(service._casting_pattern_stage([Opportunity() for _ in range(5)], [])["stage"], "Early Signals")
        self.assertEqual(service._casting_pattern_stage([Opportunity() for _ in range(10)], [])["stage"], "Emerging Patterns")
        self.assertEqual(service._casting_pattern_stage([Opportunity() for _ in range(20)], [])["stage"], "Stronger Patterns")

    def test_submission_thresholds_unlock_patterns(self):
        service = self.service()
        submissions = [Submission(current_status="Submitted") for _ in range(3)]
        outcome_submissions = [Submission(current_status="Booked") for _ in range(5)]

        self.assertEqual(service._casting_pattern_stage([], submissions)["stage"], "Emerging Patterns")
        self.assertEqual(service._casting_pattern_stage([], outcome_submissions)["stage"], "Stronger Patterns")

    def test_pattern_language_is_actor_specific(self):
        insight = self.service()._casting_pattern_row_insight("audition_type", "Self-Tape", 6)

        self.assertIn("tracked", insight)
        self.assertNotIn("industry", insight.lower())
        self.assertNotIn("national", insight.lower())


if __name__ == "__main__":
    unittest.main()
