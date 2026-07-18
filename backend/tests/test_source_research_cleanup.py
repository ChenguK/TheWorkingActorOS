from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.models import DiscoveryProviderSettings, Opportunity, SourceResearchItem
from app.schemas.discovery import SourceResearchItemCreate
from app.services.source_research_service import SourceHealthResult, SourceResearchService
from scripts.cleanup_source_and_demo_data import apply_cleanup, collect_report, is_demo_breakdown, print_report


class FakeScalarResult:
    def __init__(self, rows):
        self.rows = rows

    def __iter__(self):
        return iter(self.rows)

    def first(self):
        return self.rows[0] if self.rows else None


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class FakeDb:
    def __init__(self, source_items=None, providers=None, opportunities=None):
        self.source_items = source_items or []
        self.providers = providers or []
        self.opportunities = opportunities or []
        self.added = []
        self.committed = False

    def scalars(self, statement):
        text = str(statement)
        if "discovery_provider_settings" in text:
            return FakeScalarResult(self.providers)
        return FakeScalarResult(self.source_items)

    def get(self, model, item_id):
        rows = self.source_items if model is SourceResearchItem else self.providers
        return next((item for item in rows if getattr(item, "id", None) == item_id), None)

    def add(self, item):
        self.added.append(item)
        if isinstance(item, SourceResearchItem) and item not in self.source_items:
            self.source_items.append(item)

    def commit(self):
        self.committed = True

    def refresh(self, item):
        return None

    def query(self, model):
        if model is SourceResearchItem:
            return FakeQuery(self.source_items)
        if model is Opportunity:
            return FakeQuery(self.opportunities)
        return FakeQuery([])


class SourceResearchCleanupTests(unittest.TestCase):
    def rejected_source(self, **overrides):
        data = {
            "name": "Rejected Casting",
            "base_url": "https://rejected.example.com",
            "source_url": "https://rejected.example.com",
            "submitted_url": "https://www.rejected.example.com/casting?ref=1",
            "final_resolved_url": "https://rejected.example.com/casting",
            "redirect_target": "https://rejected.example.com/casting",
            "category": "Public casting site",
            "status": "Deleted",
            "deleted": True,
            "deleted_at": datetime.now(timezone.utc),
            "rejected_by_user": True,
            "source_health": "Active",
            "url_health_status": "Active",
            "source_usefulness": "Not Useful",
            "source_classification": "Not Useful",
        }
        data.update(overrides)
        item = SourceResearchItem(**data)
        item.id = uuid4()
        return item

    def test_reject_source_sets_deleted_fields_and_disables_provider(self):
        source = SourceResearchItem(
            name="Useful Source",
            base_url="https://useful.example.com",
            category="Public casting site",
            status="Active",
            provider_key="useful_source",
            deleted=False,
            rejected_by_user=False,
        )
        source.id = uuid4()
        provider = DiscoveryProviderSettings(
            provider_key="useful_source",
            display_name="Useful Source",
            tier=2,
            category="Public casting site",
            source_type="public_breakdowns",
            enabled=True,
            provider_metadata={},
        )
        service = SourceResearchService(FakeDb(source_items=[source], providers=[provider]))

        service.reject(source.id, "No longer useful")

        self.assertTrue(source.deleted)
        self.assertIsNotNone(source.deleted_at)
        self.assertTrue(source.rejected_by_user)
        self.assertFalse(provider.enabled)
        self.assertEqual(source.rejection_reason, "No longer useful")

    def test_deleted_source_is_not_visible_in_normal_ui_helper(self):
        service = SourceResearchService(FakeDb())
        source = self.rejected_source()

        self.assertTrue(service._matches_deleted_source({"name": "Rejected Casting", "base_url": "https://rejected.example.com"}, [source]))

    def test_find_new_sources_does_not_recreate_rejected_exact_url(self):
        source = self.rejected_source()
        service = SourceResearchService(FakeDb(source_items=[source]))

        created = service._add_suggestions([{"name": "Rejected Casting", "base_url": "https://rejected.example.com", "category": "Public casting site"}])

        self.assertEqual(created, [])

    def test_find_new_sources_does_not_recreate_rejected_normalized_domain(self):
        source = self.rejected_source()
        service = SourceResearchService(FakeDb(source_items=[source]))

        created = service._add_suggestions([{"name": "Different Name", "base_url": "http://www.rejected.example.com/jobs", "category": "Public casting site"}])

        self.assertEqual(created, [])

    def test_find_new_sources_does_not_recreate_rejected_final_resolved_url(self):
        source = self.rejected_source(base_url="https://old.example.com", source_url="https://old.example.com")
        service = SourceResearchService(FakeDb(source_items=[source]))

        created = service._add_suggestions([{"name": "Resolved URL", "base_url": "https://rejected.example.com/casting", "category": "Public casting site"}])

        self.assertEqual(created, [])

    def test_manual_source_create_cannot_recreate_previously_rejected_source(self):
        source = self.rejected_source()
        service = SourceResearchService(FakeDb(source_items=[source]))

        with self.assertRaisesRegex(ValueError, "previously rejected or deleted"):
            service.create(SourceResearchItemCreate(name="Rejected Casting", base_url="https://rejected.example.com", category="Public casting site"))

    def test_not_useful_source_is_soft_deleted(self):
        service = SourceResearchService(FakeDb())
        service._health_check = lambda _url: SourceHealthResult(
            source_health="Active",
            suggested_classification="Not Useful",
            health_reason="No actor-facing public breakdown signals were detected.",
            source_usefulness="Not Useful",
        )
        item = SourceResearchItem(name="Not Useful", base_url="https://notuseful.example.com", category="Other", status="Suggested")

        service._apply_health_check(item)

        self.assertTrue(item.deleted)
        self.assertEqual(item.status, "Deleted")
        self.assertFalse(item.rejected_by_user)

    def test_placeholder_dead_no_content_sources_stay_hidden(self):
        service = SourceResearchService(FakeDb())
        for health in ["Placeholder Website", "Dead / Unavailable Domain", "No Meaningful Content"]:
            item = SourceResearchItem(name=health, base_url="https://bad.example.com", category="Other", status="Suggested", source_health=health)
            service._soft_delete_if_bad_source(item)
            self.assertTrue(item.deleted)
            self.assertEqual(item.status, "Deleted")

    def test_demo_breakdown_detection_requires_demo_signals(self):
        demo = Opportunity(role="Detective", project="Production Websites Feature Demo", union="Unknown", location="Online", description="Demo role", is_demo_data=False)
        real = Opportunity(role="Detective", project="Untitled Procedural", union="SAG-AFTRA", location="NYC", description="Real detective role", is_demo_data=False)

        self.assertTrue(is_demo_breakdown(demo))
        self.assertFalse(is_demo_breakdown(real))

    def test_cleanup_script_dry_run_prints_without_mutation(self):
        source = SourceResearchItem(name="Bad", category="Other", status="Suggested", source_usefulness="Not Useful", deleted=False)
        source.id = uuid4()
        db = FakeDb(source_items=[source])
        report = collect_report(db)
        output = io.StringIO()

        with redirect_stdout(output):
            print_report(report, execute=False)

        self.assertIn("DRY RUN", output.getvalue())
        self.assertFalse(source.deleted)

    def test_cleanup_script_execute_soft_deletes(self):
        source = SourceResearchItem(name="Bad", category="Other", status="Suggested", source_usefulness="Not Useful", deleted=False)
        source.id = uuid4()
        report = collect_report(FakeDb(source_items=[source]))

        apply_cleanup(report)

        self.assertTrue(source.deleted)
        self.assertEqual(source.status, "Deleted")


if __name__ == "__main__":
    unittest.main()
