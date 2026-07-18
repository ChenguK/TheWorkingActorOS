import unittest

from app.db.models import SourceResearchItem
from app.services.source_research_service import SourceHealthResult, SourceResearchService


class SourceHealthCheckTests(unittest.TestCase):
    def test_placeholder_source_is_soft_deleted(self):
        service = SourceResearchService(db=None)
        service._health_check = lambda _url: SourceHealthResult(
            source_health="Placeholder Website",
            suggested_classification="Rejected",
            health_reason="Placeholder domain / no active website.",
            http_status=200,
            page_title="Looks like this domain isn't connected",
            visible_text_excerpt="Looks like this domain isn't connected to a website yet",
        )
        item = SourceResearchItem(
            name="Placeholder Casting",
            base_url="https://example-placeholder.test",
            category="Casting office",
            status="Suggested",
        )

        service._apply_health_check(item)

        self.assertTrue(item.deleted)
        self.assertEqual(item.status, "Deleted")
        self.assertEqual(item.source_health, "Placeholder Website")
        self.assertEqual(item.suggested_classification, "Rejected")
        self.assertEqual(item.rejection_reason, "Placeholder domain / no active website.")
        self.assertEqual(item.url_health_status, "Placeholder Website")
        self.assertEqual(item.source_usefulness, "Not Useful")
        self.assertEqual(item.source_classification, "Rejected")

    def test_breakdown_language_classifies_valid_source(self):
        service = SourceResearchService(db=None)

        classification, reason, usefulness = service._classify_source_text(
            "public casting calls auditions seeking actors self-tape submission instructions roles"
        )

        self.assertEqual(classification, "Valid Breakdown Source")
        self.assertEqual(usefulness, "Useful Breakdown Source")
        self.assertIn("Publicly lists", reason)

    def test_casting_office_without_breakdowns_is_not_valid_for_discovery(self):
        service = SourceResearchService(db=None)
        item = SourceResearchItem(
            name="Office",
            base_url="https://casting-office.test",
            category="Casting office",
            status="Active",
            approved_by_user=True,
            url_health_status="Active",
            source_usefulness="Useful Non-Breakdown Source",
            source_classification="Casting Office",
        )

        self.assertFalse(service._valid_breakdown_source(item))

    def test_recognized_organization_bad_url_is_rejected_by_url(self):
        service = SourceResearchService(db=None)
        service._health_check = lambda _url: SourceHealthResult(
            source_health="Placeholder Website",
            suggested_classification="Rejected",
            health_reason="Placeholder domain / no active website.",
            submitted_url="https://www.telseyandco.com/",
            final_resolved_url="https://www.telseyandco.com/",
            source_usefulness="Not Useful",
            verification_notes="Exact URL resolved to placeholder/domain parking content.",
        )
        item = SourceResearchItem(
            name="Telsey Office",
            base_url="https://www.telseyandco.com/",
            category="Casting office",
            status="Suggested",
        )

        service._apply_health_check(item)

        self.assertEqual(item.organization_legitimacy, "Recognized Organization")
        self.assertEqual(item.submitted_url, "https://www.telseyandco.com/")
        self.assertEqual(item.url_health_status, "Placeholder Website")
        self.assertEqual(item.source_usefulness, "Not Useful")
        self.assertTrue(item.deleted)
        self.assertIn("Recognized organization", item.verification_notes)


if __name__ == "__main__":
    unittest.main()
