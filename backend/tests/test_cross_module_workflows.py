import unittest
from datetime import date, datetime, timezone
from uuid import uuid4

from app.db.models import ActorJournalEntry, Asset, AuditionCalendarEvent, CareerDevelopmentTask, CastingGoal, Opportunity, Submission
from app.db.models.agent import SelfTapeWorkflow
from app.services.actor_work_event_service import ActorWorkEventService
from app.services.opportunity_service import OpportunityService
from app.services.workflow_connector_service import WorkflowConnectorService


class CrossModuleWorkflowTests(unittest.TestCase):
    def service(self) -> WorkflowConnectorService:
        return WorkflowConnectorService(db=None)

    def test_breakdown_dates_create_calendar_candidates(self):
        audition_deadline = datetime(2026, 7, 10, 17, 0, tzinfo=timezone.utc)
        callback_date = datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc)
        opportunity = Opportunity(
            role="Attorney",
            project="Legal Drama",
            project_type="Television",
            role_type="Guest Star",
            union="SAG-AFTRA",
            location="New York, NY",
            description="Self-tape guest star breakdown.",
            audition_type="Self-Tape",
            audition_deadline=audition_deadline,
            callback_date=callback_date,
            shoot_start_date=date(2026, 7, 20),
            role_details={"self_tape_submission_link": "https://casting.example/submit"},
            production_details={},
            source_metadata={},
        )

        candidates = self.service()._calendar_candidates(opportunity)

        self.assertIn(("Self-Tape Due", audition_deadline, None, False), candidates)
        self.assertTrue(any(item[0] == "Virtual Callback" or item[0] == "In-Person Callback" for item in candidates))
        self.assertTrue(any(item[0] == "Shoot" for item in candidates))

    def test_casting_goal_terms_feed_watch_lists(self):
        goal = CastingGoal(
            title="Build toward recurring TV roles",
            goal_type="Recurring",
            target_archetypes=["Attorney", "Executive"],
            target_role_types=["Guest Star"],
            target_project_types=["Television", "Streaming"],
            target_markets=["New York"],
            target_casting_offices=["Telsey"],
            priority="High",
            status="Active",
        )

        terms = self.service()._clean_terms(
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
        self.assertEqual(terms.count("Attorney"), 1)

    def test_material_upload_completes_matching_career_task(self):
        task = CareerDevelopmentTask(
            title="Create Attorney Reel Scene",
            description="Film a legal procedural scene.",
            priority="High",
            status="Not Started",
            related_archetype="Attorney",
            target_role_types=["Attorney"],
            estimated_impact="High",
            supported_archetypes=["Attorney"],
        )
        asset = Asset(
            actor_profile_id="00000000-0000-0000-0000-000000000001",
            asset_name="Attorney Reel Scene",
            asset_type="Reel",
            local_file_path="/tmp/reel.mov",
            tags=["legal"],
            archetype_names=["Attorney"],
        )

        status = self.service()._task_completion_status(task, asset)

        self.assertEqual(status, "Completed")

    def test_material_upload_partially_completes_nonmatching_career_task(self):
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

        status = self.service()._task_completion_status(task, asset)

        self.assertEqual(status, "Partially Completed")

    def test_self_tape_breakdown_creates_not_started_audition_task(self):
        class FakeDb:
            def __init__(self):
                self.added = []

            def scalar(self, _statement):
                return None

            def add(self, item):
                self.added.append(item)

        db = FakeDb()
        due_at = datetime(2026, 7, 10, 17, 0, tzinfo=timezone.utc)
        opportunity = Opportunity(
            id=uuid4(),
            role="Viv",
            project="Comedy Pilot",
            project_type="Television",
            role_type="Co-Star",
            union="SAG-AFTRA",
            location="New York, NY",
            description="Self-tape role breakdown.",
            audition_type="Self-Tape",
            audition_deadline=due_at,
            role_details={
                "self_tape_submission_link": "https://casting.example/upload",
                "preparation_instructions": "Prepare the provided sides.",
            },
            production_details={},
            source_metadata={},
        )

        OpportunityService(db)._ensure_self_tape_workflow(opportunity)

        self.assertEqual(len(db.added), 1)
        workflow = db.added[0]
        self.assertIsInstance(workflow, SelfTapeWorkflow)
        self.assertEqual(workflow.status, "Not Started")
        self.assertEqual(workflow.opportunity_id, opportunity.id)
        self.assertEqual(workflow.tape_due_at, due_at)
        self.assertEqual(workflow.upload_link, "https://casting.example/upload")

    def test_manual_self_tape_workflow_records_linked_journal_and_calendar(self):
        class FakeDb:
            def __init__(self):
                self.added = []

            def scalar(self, _statement):
                return None

            def add(self, item):
                self.added.append(item)

        db = FakeDb()
        due_at = datetime(2026, 7, 10, 17, 0, tzinfo=timezone.utc)
        opportunity = Opportunity(
            id=uuid4(),
            role="Viv",
            project="Comedy Pilot",
            project_type="Television",
            description="Self-tape role breakdown.",
            audition_type="Self-Tape",
            audition_deadline=due_at,
            role_details={"self_tape_submission_link": "https://casting.example/upload"},
        )

        OpportunityService(db)._ensure_self_tape_workflow(opportunity)
        ActorWorkEventService(db).accepted_breakdown(opportunity)

        self.assertTrue(any(isinstance(item, SelfTapeWorkflow) for item in db.added))
        journal = next(item for item in db.added if isinstance(item, ActorJournalEntry))
        calendar = next(item for item in db.added if isinstance(item, AuditionCalendarEvent))
        self.assertEqual(journal.linked_breakdown_id, opportunity.id)
        self.assertEqual(journal.event_type, "Accepted Breakdown")
        self.assertEqual(calendar.opportunity_id, opportunity.id)
        self.assertEqual(calendar.event_type, "Self-Tape Due")
        self.assertEqual(calendar.start_datetime, due_at)
        self.assertEqual(calendar.notes, "https://casting.example/upload")

    def test_submission_added_records_linked_journal_and_calendar(self):
        class FakeDb:
            def __init__(self):
                self.added = []

            def scalar(self, _statement):
                return None

            def add(self, item):
                self.added.append(item)

        db = FakeDb()
        due_at = datetime(2026, 7, 10, 17, 0, tzinfo=timezone.utc)
        opportunity = Opportunity(
            id=uuid4(),
            role="Viv",
            project="Comedy Pilot",
            audition_type="Self-Tape",
            audition_deadline=due_at,
        )
        submission = Submission(
            id=uuid4(),
            actor_profile_id=uuid4(),
            opportunity_id=opportunity.id,
            opportunity=opportunity,
            current_status="Submitted",
            submitted_at=due_at,
        )

        ActorWorkEventService(db).submission_added(submission)

        journal = next(item for item in db.added if isinstance(item, ActorJournalEntry))
        calendar = next(item for item in db.added if isinstance(item, AuditionCalendarEvent))
        self.assertEqual(journal.linked_breakdown_id, opportunity.id)
        self.assertEqual(journal.linked_audition_id, submission.id)
        self.assertEqual(calendar.opportunity_id, opportunity.id)
        self.assertEqual(calendar.submission_id, submission.id)

    def test_material_upload_event_links_asset_and_task(self):
        class FakeDb:
            def __init__(self):
                self.added = []

            def scalar(self, _statement):
                return None

            def add(self, item):
                self.added.append(item)

        task_id = uuid4()
        asset = Asset(
            id=uuid4(),
            actor_profile_id=uuid4(),
            asset_name="Authority Headshot",
            asset_type="Headshot",
            local_file_path="/tmp/headshot.jpg",
            archetype_names=["Warm Authority"],
        )

        db = FakeDb()
        ActorWorkEventService(db).material_uploaded(asset, career_task_id=task_id)

        journal = next(item for item in db.added if isinstance(item, ActorJournalEntry))
        self.assertEqual(journal.event_type, "Headshot Uploaded")
        self.assertEqual(journal.linked_material_id, asset.id)
        self.assertEqual(journal.linked_career_task_id, task_id)

    def test_callback_event_links_submission_and_breakdown(self):
        class FakeDb:
            def __init__(self):
                self.added = []

            def scalar(self, _statement):
                return None

            def add(self, item):
                self.added.append(item)

        opportunity = Opportunity(id=uuid4(), role="Viv", project="Comedy Pilot")
        submission_id = uuid4()
        db = FakeDb()

        ActorWorkEventService(db).callback_added(
            event_name="First Callback",
            opportunity=opportunity,
            opportunity_id=opportunity.id,
            submission_id=submission_id,
            notes="Prepare sides.",
            event_datetime=datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc),
        )

        journal = next(item for item in db.added if isinstance(item, ActorJournalEntry))
        self.assertEqual(journal.event_type, "Callback Received")
        self.assertEqual(journal.linked_breakdown_id, opportunity.id)
        self.assertEqual(journal.linked_audition_id, submission_id)


if __name__ == "__main__":
    unittest.main()
