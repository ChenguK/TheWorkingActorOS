from pathlib import Path
import re


SOURCE = Path(__file__).resolve().parents[2] / "frontend/src/features/workflowPanels.tsx"
SOURCE_LIBRARY = Path(__file__).resolve().parents[2] / "frontend/src/features/source-library/components/SourceLibraryPanel.tsx"
OPPORTUNITIES_PAGE = Path(__file__).resolve().parents[2] / "frontend/src/pages/OpportunitiesPage.tsx"
BREAKDOWNS_FEATURE = Path(__file__).resolve().parents[2] / "frontend/src/features/breakdowns"
BREAKDOWNS_PANEL = BREAKDOWNS_FEATURE / "components/BreakdownsPanel.tsx"
BREAKDOWNS_COMPONENTS = [
    BREAKDOWNS_FEATURE / "components/BreakdownDiscovery.tsx",
    BREAKDOWNS_FEATURE / "components/HiddenOpportunityReview.tsx",
    BREAKDOWNS_FEATURE / "components/HiddenOpportunityActionForm.tsx",
    BREAKDOWNS_FEATURE / "components/BreakdownManager.tsx",
    BREAKDOWNS_FEATURE / "components/BreakdownReadiness.tsx",
    BREAKDOWNS_FEATURE / "components/BreakdownDetails.tsx",
]


def _source_text() -> str:
    return SOURCE.read_text()


def _source_library_text() -> str:
    return SOURCE_LIBRARY.read_text()


def _breakdowns_text() -> str:
    return "\n".join(path.read_text() for path in BREAKDOWNS_COMPONENTS)


def _function_block(name: str, text: str | None = None) -> str:
    text = text or _source_text()
    start = text.index(f"function {name}")
    next_function = text.find("\nfunction ", start + 1)
    if next_function == -1:
        return text[start:]
    return text[start:next_function]


def _component_block(name: str, text: str | None = None) -> str:
    text = text or _source_text()
    start = text.index(f"export function {name}")
    next_component = text.find("\nexport function ", start + 1)
    if next_component == -1:
        return text[start:]
    return text[start:next_component]


def test_source_management_has_no_browser_prompt_editing():
    assert "window.prompt" not in _component_block("SourceLibraryPanel", _source_library_text())


def test_approved_sources_bucket_was_removed():
    text = _source_library_text()

    assert "Approved Sources" not in text
    assert 'title="Source Library"' in text
    assert "Sources for Your Approval" in text
    assert "Approved Source Library" not in text
    assert 'title: "Breakdown Sources"' in text
    assert 'title: "Casting Offices"' in text
    assert 'title: "Production Companies"' in text
    assert 'title: "Regional Resources"' in text
    assert 'title: "Watch List Sources"' in text


def test_source_row_title_is_link_without_open_source_action():
    block = _function_block("SourceRow", _source_library_text())

    assert 'href={openUrl}' in block
    assert "Open Source" not in block
    assert "onOpen" not in block


def test_approved_source_row_does_not_render_approve_action():
    block = _function_block("SourceRow", _source_library_text())

    assert "{!approved && canApproveResearch && onApprove" in block
    assert "{approved && canApproveResearch" not in block


def test_source_row_keeps_edit_and_activate_disable_actions():
    block = _function_block("SourceRow", _source_library_text())

    assert "onEdit" in block
    assert "ChevronRight" in block
    assert "ChevronDown" in block
    assert "Disable" in block
    assert "Activate" in block
    assert "Delete" in block


def test_discovery_report_and_source_library_link_are_visible():
    text = _breakdowns_text()

    assert "View Discovery Report" in text
    assert "Manage in Source Library" in text
    assert "DiscoveryReportPanel" in text


def test_breakdowns_feature_has_no_browser_prompt_editing():
    text = _breakdowns_text()

    assert "window.prompt" not in text
    assert "prompt(" not in text
    assert "window.confirm" not in text
    assert "confirm(" not in text


def test_opportunities_page_uses_merged_audition_readiness():
    text = OPPORTUNITIES_PAGE.read_text()
    panel = BREAKDOWNS_PANEL.read_text()

    assert 'import { BreakdownsPanel } from "@/features/breakdowns"' in text
    assert "MergedAuditionReadinessPanel" in panel
    assert "RecommendationPanel" not in text
    assert "MaterialOpportunityMatchPanel" not in text
    assert re.search(r"(?<!Merged)AuditionReadinessPanel", text) is None


def test_merged_audition_readiness_contains_materials_and_strategy():
    block = _component_block("MergedAuditionReadinessPanel", _breakdowns_text())

    assert 'title="Audition Readiness"' in block
    assert "RecommendedMaterialSelect" in block
    assert "*recommended" in _function_block("RecommendedMaterialSelect", _breakdowns_text())
    assert 'label="Strategy"' in block
    assert 'label="Why This Role Fits"' in block


def test_breakdowns_feature_owns_form_discovery_review_and_recommendations():
    text = _breakdowns_text()

    assert "export function OpportunityManager" in text
    assert "export function AutomationDashboard" in text
    assert "export function MergedAuditionReadinessPanel" in text
    assert "export function RecommendationPanel" in text
    assert "Add Breakdown" in text
    assert "Find Film/TV Breakdowns" in text
    assert "Travel Exceptions / Needs Review" in text
    assert "Character Breakdown" in text
    assert "Audition/Tape Due Date" in text


def test_workflow_panels_keeps_only_breakdown_compatibility_exports():
    assert not SOURCE.exists()
