import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from app.automation.discovery.contracts import NormalizedOpportunity
from app.services.breakdown_deadline_service import BreakdownDeadlineService
from app.services.breakdown_details_service import BreakdownDetailsService


NOW = datetime(2026, 7, 5, 12, 0, tzinfo=ZoneInfo("America/New_York"))


class BreakdownDeadlineServiceTests(unittest.TestCase):
    def test_expired_submission_deadline_is_rejected(self):
        result = BreakdownDeadlineService().validate_facts(
            {"submission_deadline": "June 21, 2026"},
            now=NOW,
        )

        self.assertTrue(result.expired)
        self.assertIn("submission deadline has passed", result.reason or "")

    def test_active_submission_deadline_is_accepted(self):
        result = BreakdownDeadlineService().validate_facts(
            {"submission_deadline": "July 21, 2026"},
            now=NOW,
        )

        self.assertEqual(result.status, "Valid")

    def test_posted_date_is_not_treated_as_due_date(self):
        result = BreakdownDeadlineService().validate_facts(
            {"posted_date": "June 21, 2026"},
            now=NOW,
        )

        self.assertEqual(result.status, "Valid")

    def test_shoot_date_is_not_treated_as_due_date(self):
        result = BreakdownDeadlineService().validate_facts(
            {"shoot_or_work_dates": "June 21, 2026"},
            now=NOW,
        )

        self.assertEqual(result.status, "Valid")

    def test_uncertain_deadline_needs_date_review(self):
        result = BreakdownDeadlineService().validate_facts(
            {"submission_deadline": "early next week"},
            now=NOW,
        )

        self.assertTrue(result.needs_review)

    def test_breakdown_parser_separates_date_facts(self):
        parsed = BreakdownDetailsService().from_text(
            """
            Posted Date
            June 21, 2026
            Submission Deadline
            July 21, 2026
            Shoot Dates
            August 1, 2026
            Role
            Attorney
            Seeking actors for a streaming drama.
            """
        )

        self.assertEqual(parsed["extracted_facts"]["dates"]["posted_date"], "June 21, 2026")
        self.assertEqual(parsed["extracted_facts"]["dates"]["submission_deadline"], "July 21, 2026")
        self.assertEqual(parsed["extracted_facts"]["dates"]["shoot_or_work_dates"], "August 1, 2026")

    def test_normalized_expired_deadline_is_rejected(self):
        item = NormalizedOpportunity(
            role="Attorney",
            project="Streaming Drama",
            union="SAG-AFTRA",
            location="Philadelphia, PA",
            description="Seeking actors.",
            original_post_url="https://example.com/breakdown",
            audition_type="Self-Tape",
            audition_travel_hours=None,
            role_details={"self_tape_due_date": "June 21, 2026"},
        )

        result = BreakdownDeadlineService().validate_normalized(item, now=NOW)

        self.assertTrue(result.expired)


if __name__ == "__main__":
    unittest.main()
