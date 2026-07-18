from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CAREER_PAGE = ROOT / "frontend/src/pages/CareerPage.tsx"
CAREER_FEATURE = ROOT / "frontend/src/features/career-intelligence"
CAREER_PANEL = CAREER_FEATURE / "components/CareerIntelligencePanel.tsx"
CAREER_LEGACY_PANELS = CAREER_FEATURE / "components/CareerLegacyPanels.tsx"
CHIEF_OF_STAFF_FEATURE = ROOT / "frontend/src/features/chief-of-staff"
WORKFLOW_PANELS = ROOT / "frontend/src/features/workflowPanels.tsx"


def test_career_page_is_thin_feature_composition():
    text = CAREER_PAGE.read_text()

    assert 'import { CareerIntelligencePanel } from "@/features/career-intelligence"' in text
    assert "function CareerRoadmapSection" not in text
    assert "CareerDevelopmentDashboard" not in text
    assert len(text.splitlines()) <= 20


def test_career_feature_owns_planning_and_learning_sections():
    text = CAREER_PANEL.read_text()

    assert 'title="Career Planning"' in text
    assert 'subtitle="What should I build next?"' in text
    assert 'title="Career Intelligence"' in text
    assert 'subtitle="What have I learned about my career?"' in text
    assert 'title="Career SWOT Analysis"' in text
    assert "Strengths • Weaknesses • Opportunities • Threats" in text
    assert "id=\"script-finder\"" in text


def test_career_legacy_panels_moved_out_of_workflow_panels():
    feature_text = CAREER_LEGACY_PANELS.read_text()
    chief_of_staff_text = "\n".join(path.read_text() for path in CHIEF_OF_STAFF_FEATURE.rglob("*.ts*"))

    assert not WORKFLOW_PANELS.exists()
    assert "export function CareerDevelopmentDashboard" in feature_text
    assert "export function AIIntelligencePanel" in feature_text
    assert "export function ChiefOfStaffPanel" in chief_of_staff_text
    assert "export function ExecutiveIntelligencePanel" not in feature_text


def test_career_feature_does_not_import_unrelated_feature_internals():
    feature_text = "\n".join(path.read_text() for path in CAREER_FEATURE.rglob("*.ts*"))

    assert "workflowPanels" not in feature_text
    assert "features/materials/components" not in feature_text
    assert "features/relationships/components" not in feature_text
    assert "features/analytics/components" not in feature_text
    assert "features/script-finder/components" not in feature_text
    assert "features/script-finder/hooks" not in feature_text
