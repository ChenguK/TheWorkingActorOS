from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RELATIONSHIPS_PAGE = ROOT / "frontend/src/pages/RelationshipsPage.tsx"
RELATIONSHIPS_FEATURE = ROOT / "frontend/src/features/relationships"
RELATIONSHIPS_PANEL = RELATIONSHIPS_FEATURE / "components/RelationshipsPanel.tsx"
RELATIONSHIP_FORM = RELATIONSHIPS_FEATURE / "components/RelationshipForm.tsx"
RELATIONSHIP_LIST = RELATIONSHIPS_FEATURE / "components/RelationshipList.tsx"
COMMUNICATION_LOG_PANEL = RELATIONSHIPS_FEATURE / "components/CommunicationLogPanel.tsx"
RELATIONSHIPS_INDEX = RELATIONSHIPS_FEATURE / "index.ts"
WORKFLOW_PANELS = ROOT / "frontend/src/features/workflowPanels.tsx"
AUDITIONS_PAGE = ROOT / "frontend/src/pages/AuditionsPage.tsx"


def test_relationships_page_is_thin_composition_layer():
    text = RELATIONSHIPS_PAGE.read_text()
    assert 'import { RelationshipsPanel } from "@/features/relationships"' in text
    assert "AuditionHistoryPanel" not in text
    assert "CommunicationLogPanel" not in text
    assert len(text.splitlines()) <= 60


def test_relationships_feature_owns_relationship_and_communication_ui():
    panel = RELATIONSHIPS_PANEL.read_text()
    form = RELATIONSHIP_FORM.read_text()
    relationship_list = RELATIONSHIP_LIST.read_text()
    communication = COMMUNICATION_LOG_PANEL.read_text()

    assert "Relationship History" in panel
    assert "RelationshipInsights" in panel
    assert "Add Relationship" in panel
    assert "Name" in form
    assert "Company / Office" in form
    assert "Linked Breakdowns" in form
    assert "Linked Submissions" in form
    assert "Save Relationship" in relationship_list
    assert "ConfirmAction" in relationship_list
    assert "Agent Communication Log" in communication
    assert "Add Communication" in communication
    assert "Follow-up needed" in communication


def test_relationships_public_api_exports_intentional_surface_only():
    text = RELATIONSHIPS_INDEX.read_text()
    assert "RelationshipsPanel" in text
    assert "CommunicationLogPanel" in text
    assert "../../pages/RelationshipsPage" not in text
    assert "../workflowPanels" not in text
    assert "AuditionHistoryPanel" not in text


def test_relationships_page_does_not_consume_relationship_workflow_snapshots():
    text = RELATIONSHIPS_PAGE.read_text()
    assert "data.relationships" not in text
    assert "data.communicationLogs" not in text
    assert "data.relationshipAnalytics" not in text
    assert "data.onChanged" not in text


def test_relationships_feature_does_not_import_pages_auditions_or_workflow_panels():
    for path in RELATIONSHIPS_FEATURE.rglob("*.ts*"):
        text = path.read_text()
        assert "workflowPanels" not in text
        assert "pages/RelationshipsPage" not in text
        assert "features/auditions" not in text


def test_workflow_panels_no_longer_owns_relationships_or_communication_logs():
    assert not WORKFLOW_PANELS.exists()


def test_auditions_page_no_longer_passes_relationship_data_to_audition_history():
    text = AUDITIONS_PAGE.read_text()
    assert "relationshipAnalytics={data.relationshipAnalytics}" not in text
    assert "relationships={data.relationships}" not in text
    assert "selfTapeAnalytics={data.selfTapeAnalytics}" not in text
