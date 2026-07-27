from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUDITIONS_PAGE = ROOT / "frontend/src/pages/AuditionsPage.tsx"
AUDITIONS_FEATURE = ROOT / "frontend/src/features/auditions"
AUDITIONS_PANEL = AUDITIONS_FEATURE / "components/AuditionsPanel.tsx"
SUBMISSION_TRACKER = AUDITIONS_FEATURE / "components/SubmissionTracker.tsx"
CALLBACK_EVENTS = AUDITIONS_FEATURE / "components/CallbackEventsPanel.tsx"
AUDITION_NOTES = AUDITIONS_FEATURE / "components/AuditionNotesPanel.tsx"
AUDITION_NOTE_FORM = AUDITIONS_FEATURE / "components/AuditionPerformanceNoteForm.tsx"
SUBMISSION_HOOK = AUDITIONS_FEATURE / "hooks/useSubmissionTracker.ts"
CALLBACK_HOOK = AUDITIONS_FEATURE / "hooks/useCallbackEvents.ts"
NOTES_HOOK = AUDITIONS_FEATURE / "hooks/useAuditionNotes.ts"
QUERY_HOOK = AUDITIONS_FEATURE / "hooks/useAuditionQueries.ts"
AUDITIONS_INDEX = AUDITIONS_FEATURE / "index.ts"
WORKFLOW_PANELS = ROOT / "frontend/src/features/workflowPanels.tsx"


def test_auditions_page_is_thin_composition_layer():
    text = AUDITIONS_PAGE.read_text()
    assert 'import { AuditionsPanel } from "@/features/auditions"' in text
    assert "SubmissionTracker" not in text
    assert "CallbackEventsPanel" not in text
    assert "AuditionHistoryPanel" not in text
    assert len(text.splitlines()) <= 60


def test_auditions_feature_owns_submission_callbacks_and_private_notes():
    panel = AUDITIONS_PANEL.read_text()
    tracker = SUBMISSION_TRACKER.read_text()
    callbacks = CALLBACK_EVENTS.read_text()
    notes = AUDITION_NOTES.read_text()

    assert "SubmissionTracker" in panel
    assert "CallbackEventsPanel" in panel
    assert "AuditionNotesPanel" in panel
    assert "Submitted/Auditioned for this role" in tracker
    assert "Self-Tapes" in tracker
    assert "Parse Audition Details" in tracker
    assert "Callback Events" in callbacks
    assert "Add Callback Event" in callbacks
    assert "Private Audition Journal" in notes
    assert "Add Journal Entry" in notes
    assert "AuditionPerformanceNoteForm" in notes


def test_auditions_hooks_own_mutation_workflows():
    submission_hook = SUBMISSION_HOOK.read_text()
    callback_hook = CALLBACK_HOOK.read_text()
    notes_hook = NOTES_HOOK.read_text()
    query_hook = QUERY_HOOK.read_text()

    assert "useCreateSubmission" in submission_hook
    assert "createSelfTapeTask" in submission_hook
    assert "createAuditionCalendarEvent" not in submission_hook
    assert "dates are added to your calendar automatically" in SUBMISSION_TRACKER.read_text()
    assert "createAuditionNote" in submission_hook
    assert "useCreateCallbackEvent" in callback_hook
    assert "useDeleteCallbackEvent" in callback_hook
    assert "useCreateAuditionPerformanceNote" in notes_hook
    assert "useUpdateAuditionPerformanceNote" in notes_hook
    assert "useMutation" in query_hook
    assert "recordSubmission" in query_hook


def test_auditions_private_note_editing_uses_real_form_not_browser_prompt():
    panel = AUDITION_NOTES.read_text()
    form = AUDITION_NOTE_FORM.read_text()
    hook = NOTES_HOOK.read_text()

    feature_text = "\n".join(path.read_text() for path in AUDITIONS_FEATURE.rglob("*.ts*"))
    assert "window.prompt" not in feature_text
    assert "prompt(" not in feature_text
    assert "window.confirm" not in feature_text
    assert "confirm(" not in feature_text

    assert "Edit Performance" in panel
    assert "ConfirmAction" in panel
    assert "Save Private Notes" in form
    assert "edit_audition_performance_notes" in form
    assert "edit_audition_preparation_notes" in form
    assert "Could not save these private audition notes." in form
    assert "updateEntry" in hook


def test_auditions_public_api_exports_intentional_surface_only():
    text = AUDITIONS_INDEX.read_text()
    assert "AuditionsPanel" in text
    assert "SubmissionTracker" in text
    assert "CallbackEventsPanel" in text
    assert "../../pages/AuditionsPage" not in text
    assert "../workflowPanels" not in text


def test_auditions_feature_does_not_import_pages_or_workflow_panels():
    for path in AUDITIONS_FEATURE.rglob("*.ts*"):
        text = path.read_text()
        assert "workflowPanels" not in text
        assert "pages/AuditionsPage" not in text
        assert "features/relationships/components" not in text
        assert "features/materials/components" not in text


def test_workflow_panels_no_longer_owns_auditions():
    assert not WORKFLOW_PANELS.exists()
