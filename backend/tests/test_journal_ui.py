from pathlib import Path


ROOT = Path(__file__).resolve().parents[1].parent
JOURNAL_PAGE = ROOT / "frontend/src/pages/JournalPage.tsx"
JOURNAL_PANEL = ROOT / "frontend/src/features/journal/components/JournalPanel.tsx"
JOURNAL_HOOK = ROOT / "frontend/src/features/journal/hooks/useJournalEntries.ts"
JOURNAL_UTILS = ROOT / "frontend/src/features/journal/utils/index.ts"
JOURNAL_INDEX = ROOT / "frontend/src/features/journal/index.ts"
TOP_NAVIGATION = ROOT / "frontend/src/layout/TopNavigation.tsx"


def test_journal_page_is_composition_layer():
    text = JOURNAL_PAGE.read_text()

    assert 'import { JournalPanel } from "@/features/journal"' in text
    assert "createJournalEntry" not in text
    assert "updateJournalEntryNotes" not in text
    assert "groupJournalEntriesByDate" not in text
    assert len(text.splitlines()) <= 40


def test_journal_feature_owns_form_grouping_and_links():
    panel = JOURNAL_PANEL.read_text()
    hook = JOURNAL_HOOK.read_text()
    utils = JOURNAL_UTILS.read_text()

    assert "Add Journal Entry" in panel
    assert "Save Entry" in panel
    assert "Edit notes" in panel
    assert "Save Notes" in panel
    assert "Daily View" in panel
    assert "Your meaningful actor work will collect here automatically" in panel
    assert "createJournalEntry" in hook
    assert "updateJournalEntryNotes" in hook
    assert "groupJournalEntriesByDate" in utils
    assert "formatJournalDate" in utils
    assert "journalEntryLinks" in utils


def test_journal_public_api_exports_intentional_boundary():
    text = JOURNAL_INDEX.read_text()

    assert "JournalPanel" in text
    assert "useJournalEntries" in text
    assert "../../pages/JournalPage" not in text
    assert "../workflowPanels" not in text


def test_journal_internals_do_not_import_pages_or_workflow_panels():
    for path in (ROOT / "frontend/src/features/journal").rglob("*.ts*"):
        text = path.read_text()
        assert "workflowPanels" not in text
        assert "pages/JournalPage" not in text


def test_journal_stays_in_top_navigation():
    text = TOP_NAVIGATION.read_text()

    assert '{ label: "Journal", to: "/journal" }' in text
