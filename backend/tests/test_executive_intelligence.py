import unittest

from app.db.models import Asset, CareerDevelopmentTask, CastingGoal, Opportunity
from app.services.executive_intelligence_service import ExecutiveIntelligenceService
from app.services.workflow_connector_service import WorkflowConnectorService


class ExecutiveIntelligenceTests(unittest.TestCase):
    def test_casting_goal_terms_preserve_actor_priorities(self):
        goal = CastingGoal(
            title="Book more recurring TV roles",
            goal_type="Recurring",
            target_archetypes=["Attorney", "Executive"],
            target_role_types=["Guest Star"],
            target_project_types=["Streaming"],
            target_markets=["New York"],
            target_casting_offices=["Telsey"],
            priority="High",
            status="Active",
        )

        terms = WorkflowConnectorService(db=None)._clean_terms(
            [
                goal.title,
                goal.goal_type,
                *goal.target_archetypes,
                *goal.target_role_types,
                *goal.target_project_types,
                *goal.target_markets,
                *goal.target_casting_offices,
            ]
        )

        self.assertIn("Attorney", terms)
        self.assertIn("Streaming", terms)
        self.assertIn("Telsey", terms)

    def test_material_task_completion_distinguishes_partial_matches(self):
        task = CareerDevelopmentTask(
            title="Create Detective Self-Tape",
            description="Film an investigative scene.",
            priority="Medium",
            status="Not Started",
            related_archetype="Detective",
            target_role_types=["Detective"],
            estimated_impact="High",
            supported_archetypes=["Detective"],
        )
        asset = Asset(
            actor_profile_id="00000000-0000-0000-0000-000000000001",
            asset_name="Corporate Headshot",
            asset_type="Headshot",
            local_file_path="/tmp/headshot.jpg",
            tags=["corporate"],
            archetype_names=["Executive"],
        )

        status = WorkflowConnectorService(db=None)._task_completion_status(task, asset)

        self.assertEqual(status, "Partially Completed")

    def test_breakdown_similarity_terms_include_role_project_and_archetype(self):
        opportunity = Opportunity(
            role="Attorney",
            project="Legal Drama",
            project_type="Television",
            role_type="Guest Star",
            union="SAG-AFTRA",
            location="New York",
            description="A sharp legal procedural role.",
            archetypes=["Authority Figure"],
        )

        terms = ExecutiveIntelligenceService(db=None)._terms(opportunity)

        self.assertIn("attorney", terms)
        self.assertIn("legal", terms)
        self.assertIn("authority", terms)


if __name__ == "__main__":
    unittest.main()
