import unittest

from app.automation.discovery.classification import classify_breakdown_text


class BreakdownClassificationTests(unittest.TestCase):
    def test_casting_coordinator_job_is_rejected(self):
        result = classify_breakdown_text("Casting Coordinator, Goodman Theatre. Full-time staff position with benefits.")

        self.assertEqual(result.classification, "Non-Acting Job")
        self.assertIn("employment/job listing", result.rejection_reason or "")

    def test_casting_assistant_job_is_rejected(self):
        result = classify_breakdown_text("Casting Assistant needed for regional theatre. Part-time administrative job opening.")

        self.assertEqual(result.classification, "Non-Acting Job")

    def test_actor_casting_call_is_accepted(self):
        result = classify_breakdown_text(
            "Casting call seeking actors for a streaming drama. Role: Attorney. SAG-AFTRA. Submit headshot and resume."
        )

        self.assertEqual(result.classification, "Acting Role")

    def test_self_tape_role_is_accepted(self):
        result = classify_breakdown_text(
            "Self-tape audition for Detective. Sides provided. Shoot dates in August. Role type: Guest Star."
        )

        self.assertEqual(result.classification, "Acting Role")

    def test_voiceover_role_is_accepted(self):
        result = classify_breakdown_text(
            "Voiceover talent needed for commercial campaign. Remote audition and callback possible."
        )

        self.assertEqual(result.classification, "Voiceover Role")


if __name__ == "__main__":
    unittest.main()
