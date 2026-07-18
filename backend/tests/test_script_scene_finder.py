import unittest
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import patch

from app.db.models import CareerDevelopmentTask, ScriptSource
from app.services.intelligence_service import IntelligenceService


class FakeScalarResult:
    def __init__(self, rows):
        self.rows = rows

    def __iter__(self):
        return iter(self.rows)


class FakeDb:
    def __init__(self, sources=None, task=None):
        self.sources = sources or []
        self.task = task
        self.added = []

    def get(self, model, item_id):
        if model is CareerDevelopmentTask and self.task and self.task.id == item_id:
            return self.task
        return None

    def scalars(self, _statement):
        return FakeScalarResult(self.sources)

    def add(self, item):
        self.added.append(item)

    def commit(self):
        return None

    def refresh(self, item):
        return None


class ScriptSceneFinderTests(unittest.TestCase):
    def setUp(self):
        self.settings_patch = patch(
            "app.services.intelligence_service.get_settings",
            return_value=SimpleNamespace(web_search_provider="none", parallel_api_key=None),
        )
        self.settings_patch.start()
        self.addCleanup(self.settings_patch.stop)

    def test_original_scene_brief_created_when_no_rights_safe_source_exists(self):
        task = CareerDevelopmentTask(
            title="Create Attorney Reel Scene",
            related_archetype="Attorney",
            target_role_types=["Attorney"],
            supported_archetypes=["Attorney"],
        )
        task.id = uuid4()
        source = ScriptSource(
            name="Research-only Script Database",
            source_type="Licensed database",
            rights_status="Permission Required",
            approved=True,
        )
        service = IntelligenceService(FakeDb(sources=[source], task=task))

        candidates = service.find_scene_candidates(type("Payload", (), {
            "career_task_id": task.id,
            "target_archetype": None,
            "material_goal": None,
        })())

        self.assertTrue(any(candidate.action_status == "Original Brief" for candidate in candidates))
        original = next(candidate for candidate in candidates if candidate.action_status == "Original Brief")
        self.assertEqual(original.rights_status, "Original / User-Owned")
        self.assertEqual(original.scene_brief["label"], "Original scene brief — not a copied script.")

    def test_rights_safe_source_does_not_require_original_fallback(self):
        source = ScriptSource(
            name="Royalty-Free Practice Scenes",
            source_type="Royalty-free scenes",
            rights_status="Royalty-Free",
            approved=True,
        )
        service = IntelligenceService(FakeDb(sources=[source]))
        service._fetch_visible_text = lambda url: ("Practice scenes and script library for actors.", False)

        candidates = service.find_scene_candidates(type("Payload", (), {
            "career_task_id": None,
            "target_archetype": "Mom",
            "material_goal": "Create Mom Comedy Reel Scene",
        })())

        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0].rights_status, "Royalty-Free")
        self.assertEqual(candidates[0].result_type, "Script Library")
        self.assertEqual(candidates[0].action_status, "Candidate")
        self.assertTrue(any(candidate.action_status == "Original Brief" for candidate in candidates))

    def test_parallel_search_is_called_when_configured(self):
        calls = []

        class FakeParallel:
            def __init__(self, api_key):
                self.api_key = api_key

            def search(self, **kwargs):
                calls.append(kwargs)
                return {
                    "results": [
                        {
                            "url": "https://example.com/royalty-free-attorney-scene",
                            "title": "Royalty-Free Attorney Practice Scene",
                            "snippet": "Royalty-free acting scene for an attorney reel clip.",
                        }
                    ]
                }

        service = IntelligenceService(FakeDb())
        service._fetch_visible_text = lambda url: ("Character 1: I object. Character 2: You cannot stop this. Royalty-free acting scene for actors and showreels.", False)
        with patch("app.services.intelligence_service.get_settings", return_value=SimpleNamespace(web_search_provider="parallel", parallel_api_key="key")):
            with patch.dict("sys.modules", {"parallel": SimpleNamespace(Parallel=FakeParallel)}):
                candidates = service._parallel_scene_candidates("Attorney", "Create Attorney Reel Scene", None)

        self.assertTrue(calls)
        self.assertEqual(candidates[0].rights_status, "Royalty-Free")
        self.assertEqual(candidates[0].result_type, "Specific Scene")
        self.assertIn("60-90 second reel clip", calls[0]["objective"])

    def test_copyrighted_unknown_rights_are_not_treated_as_safe(self):
        service = IntelligenceService(FakeDb())
        self.assertEqual(service._classify_scene_rights("Famous TV Script", "episode script transcript", ""), "Unknown")
        self.assertTrue(service._looks_like_copyrighted_film_tv_script("Famous TV Script", "episode script transcript", ""))

    def test_original_only_request_creates_original_brief(self):
        service = IntelligenceService(FakeDb())
        candidates = service.find_scene_candidates(type("Payload", (), {
            "career_task_id": None,
            "target_archetype": "Executive",
            "material_goal": "Create Executive Reel Scene",
            "generate_original_only": True,
        })())

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].action_status, "Original Brief")
        self.assertEqual(candidates[0].rights_status, "Original / User-Owned")
        self.assertEqual(candidates[0].result_type, "Specific Scene")

    def test_music_site_is_rejected(self):
        service = IntelligenceService(FakeDb())

        result_type = service._classify_scene_result_type(
            "Detective Background Music",
            "Stock music and sound effects for detective scenes.",
            "https://proudmusiclibrary.com/en/tag/detective",
        )

        self.assertEqual(result_type, "Music / Sound Library")

    def test_resource_guide_and_script_library_are_not_primary_scene_options(self):
        service = IntelligenceService(FakeDb())

        guide = service._classify_scene_result_type(
            "ActOnCue script resources",
            "Where to find acting scripts and monologue resources.",
            "https://actoncue.com/scripts",
        )
        library = service._classify_scene_result_type(
            "StageMilk Scenes",
            "A library of practice scenes for actors.",
            "https://www.stagemilk.com/scenes",
        )

        self.assertEqual(guide, "Resource Guide")
        self.assertEqual(library, "Script Library")

    def test_specific_scene_appears_as_scene_option(self):
        service = IntelligenceService(FakeDb())

        result_type = service._classify_scene_result_type(
            "Royalty-Free Attorney Scene",
            "Character 1: You buried the evidence. Character 2: You cannot prove that. Royalty-free practice scene for actors and showreels.",
            "https://example.com/attorney-scene",
        )

        self.assertEqual(result_type, "Specific Scene")

    def test_fetch_failed_result_is_hidden(self):
        service = IntelligenceService(FakeDb())

        result_type = service._classify_scene_result_type(
            "AuditionScript lead",
            "",
            "https://auditionscript.example/missing",
            fetch_failed=True,
        )

        self.assertEqual(result_type, "Dead / Fetch Failed")

    def test_approved_material_plan_drives_query_generation(self):
        task = CareerDevelopmentTask(title="Create Attorney Reel Scene", related_archetype="Attorney")
        task.id = uuid4()
        plan = SimpleNamespace(
            id=uuid4(),
            career_task_id=task.id,
            missing_asset="Attorney Reel Scene",
            target_archetype="Attorney",
            plan_status="Approved",
            plan={"scene_concept": "Attorney cross-examination scene"},
        )
        service = IntelligenceService(FakeDb(task=task))
        service.db.get = lambda model, item_id: task if model is CareerDevelopmentTask else plan

        candidates = service.find_scene_candidates(type("Payload", (), {
            "career_task_id": task.id,
            "material_plan_id": plan.id,
            "target_archetype": None,
            "material_goal": None,
            "generate_original_only": True,
        })())

        self.assertEqual(candidates[0].scene_brief["character_type"], "Attorney")

    def test_denied_material_plan_does_not_search(self):
        plan = SimpleNamespace(
            id=uuid4(),
            career_task_id=None,
            missing_asset="Detective Scene",
            target_archetype="Detective",
            plan_status="Denied",
            plan={},
        )
        service = IntelligenceService(FakeDb())
        service.db.get = lambda model, item_id: plan

        candidates = service.find_scene_candidates(type("Payload", (), {
            "career_task_id": None,
            "material_plan_id": plan.id,
            "target_archetype": None,
            "material_goal": None,
            "generate_original_only": False,
        })())

        self.assertEqual(candidates, [])

    def test_scene_finder_button_and_actions_are_present(self):
        source = Path(__file__).resolve().parents[2] / "frontend" / "src" / "features" / "script-finder" / "components" / "ScriptFinderPanel.tsx"
        text = source.read_text()
        self.assertIn("Find Scene Options", text)
        self.assertIn("Approve Plan", text)
        self.assertIn("Deny Plan", text)
        self.assertIn("Scene Options", text)
        self.assertIn("Resources to Browse", text)
        self.assertIn("Save Scene Idea", text)
        self.assertIn("Mark Permission Requested", text)
        self.assertIn("Generate Original Scene Brief", text)


if __name__ == "__main__":
    unittest.main()
