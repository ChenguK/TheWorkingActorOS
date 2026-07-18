from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MATERIALS_PAGE = ROOT / "frontend/src/pages/MaterialsPage.tsx"
MATERIALS_PANEL = ROOT / "frontend/src/features/materials/components/MaterialsPanel.tsx"
ASSET_LIBRARY = ROOT / "frontend/src/features/materials/components/AssetLibrary.tsx"
SELF_TAPE_LIBRARY = ROOT / "frontend/src/features/materials/components/SelfTapeLibraryPanel.tsx"
MATERIAL_EDIT_FORM = ROOT / "frontend/src/features/materials/components/MaterialEditForm.tsx"
SELF_TAPE_OUTCOME_FORM = ROOT / "frontend/src/features/materials/components/SelfTapeOutcomeForm.tsx"
MATERIALS_INDEX = ROOT / "frontend/src/features/materials/index.ts"
WORKFLOW_PANELS = ROOT / "frontend/src/features/workflowPanels.tsx"


def test_materials_page_is_thin_composition_layer():
    text = MATERIALS_PAGE.read_text()
    assert 'import { MaterialsPanel } from "@/features/materials"' in text
    assert "AuditionHistoryPanel" not in text
    assert "AssetLibrary" not in text
    assert len(text.splitlines()) <= 60


def test_materials_feature_owns_asset_library_and_self_tape_library():
    asset_library = ASSET_LIBRARY.read_text()
    self_tape_library = SELF_TAPE_LIBRARY.read_text()
    panel = MATERIALS_PANEL.read_text()

    assert "Upload Material" in asset_library
    assert "useUploadMaterial" in (ROOT / "frontend/src/features/materials/hooks/useMaterialLibrary.ts").read_text()
    assert "uploadMaterial" in (ROOT / "frontend/src/features/materials/hooks/useMaterials.ts").read_text()
    assert "AI-assisted tags" in asset_library
    assert "Suggested Tags" in asset_library
    assert "Self-Tape Library" in self_tape_library
    assert "Add Self-Tape" in self_tape_library
    assert "useCreateReusableSelfTape" in (ROOT / "frontend/src/features/materials/hooks/useSelfTapeLibrary.ts").read_text()
    assert "createSelfTape" in (ROOT / "frontend/src/features/materials/hooks/useReusableSelfTapes.ts").read_text()
    assert "AssetLibrary" in panel
    assert "SelfTapeLibraryPanel" in panel


def test_materials_editing_uses_real_forms_not_browser_prompts():
    materials_text = "\n".join(path.read_text() for path in (ROOT / "frontend/src/features/materials").rglob("*.ts*"))
    material_form = MATERIAL_EDIT_FORM.read_text()
    outcome_form = SELF_TAPE_OUTCOME_FORM.read_text()
    asset_library = ASSET_LIBRARY.read_text()
    self_tape_library = SELF_TAPE_LIBRARY.read_text()

    assert "window.prompt" not in materials_text
    assert "prompt(" not in materials_text
    assert "window.confirm" not in materials_text
    assert "confirm(" not in materials_text
    assert "Material Name" in material_form
    assert "Freshness Status" in material_form
    assert "Save Material" in material_form
    assert "Backend errors are visible" not in material_form
    assert "Outcome" in outcome_form
    assert "Save Self-Tape" in outcome_form
    assert "ConfirmAction" in asset_library
    assert "ConfirmAction" in self_tape_library


def test_materials_public_api_exports_only_materials_feature_surface():
    text = MATERIALS_INDEX.read_text()
    assert "MaterialsPanel" in text
    assert "AssetLibrary" in text
    assert "SelfTapeLibraryPanel" in text
    assert "../../pages/MaterialsPage" not in text
    assert "../workflowPanels" not in text
    assert "PlatformProfileImportAssistant" not in text
    assert "MaterialPerformancePanel" not in text


def test_materials_page_does_not_consume_asset_workflow_snapshot():
    text = MATERIALS_PAGE.read_text()
    assert "data.assets" not in text
    assert '"assets"' not in text


def test_materials_feature_does_not_import_pages_or_workflow_panels():
    for path in (ROOT / "frontend/src/features/materials").rglob("*.ts*"):
      text = path.read_text()
      assert "workflowPanels" not in text
      assert "pages/MaterialsPage" not in text


def test_workflow_panels_keeps_only_asset_library_compatibility_export():
    assert not WORKFLOW_PANELS.exists()
