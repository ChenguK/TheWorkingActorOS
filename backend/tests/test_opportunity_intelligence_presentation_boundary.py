from __future__ import annotations

import ast
import json
from pathlib import Path

from app.schemas.opportunity import OpportunityRead
from app.services.opportunity_intelligence_summary import (
    serialize_command_center_intelligence,
)
from tests.intelligence_builders import FIXED_OPPORTUNITY_ID, fixed_as_of


BACKEND_APP = Path(__file__).parents[1] / "app"
COMMAND_CENTER_OWNER = BACKEND_APP / "services" / "command_center_service.py"
SUMMARY_MODULE = BACKEND_APP / "services" / "opportunity_intelligence_summary.py"


def _production_python_files() -> list[Path]:
    return sorted(BACKEND_APP.rglob("*.py"))


def _imports_symbol(path: Path, module: str, symbol: str) -> bool:
    tree = ast.parse(path.read_text())
    return any(
        isinstance(node, ast.ImportFrom)
        and node.module == module
        and any(alias.name == symbol for alias in node.names)
        for node in ast.walk(tree)
    )


def _calls_method(path: Path, method_name: str) -> bool:
    tree = ast.parse(path.read_text())
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == method_name
        for node in ast.walk(tree)
    )


def _serialized_opportunity() -> dict:
    item = OpportunityRead(
        id=FIXED_OPPORTUNITY_ID,
        created_at=fixed_as_of(),
        updated_at=fixed_as_of(),
        role="Detective",
        project="Fictional Procedural",
        union="SAG-AFTRA",
        location="New York, NY",
        description="A deterministic fictional acting opportunity.",
    )
    return item.model_dump(mode="json")


def _compact_size(value: object) -> int:
    return len(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def test_opportunity_contracts_do_not_expose_command_center_intelligence():
    assert "intelligence" not in OpportunityRead.model_fields

    payload = _serialized_opportunity()

    assert "intelligence" not in payload
    assert "overall_score" not in payload
    assert "action_reason_code" not in payload


def test_current_opportunity_detail_and_list_payload_sizes_are_characterized():
    payload = _serialized_opportunity()

    assert _compact_size(payload) == 1_766
    assert _compact_size([payload] * 8) == 14_137
    assert _compact_size([payload] * 100) == 176_701


def test_command_center_is_the_only_summary_serializer_importer():
    importers = {
        path.relative_to(BACKEND_APP).as_posix()
        for path in _production_python_files()
        if _imports_symbol(
            path,
            "app.services.opportunity_intelligence_summary",
            "serialize_command_center_intelligence",
        )
    }

    assert importers == {"services/command_center_service.py"}
    assert serialize_command_center_intelligence is not None


def test_no_second_production_ranking_score_path_exists():
    score_callers = {
        path.relative_to(BACKEND_APP).as_posix()
        for path in _production_python_files()
        if path != SUMMARY_MODULE and _calls_method(path, "score")
    }

    assert score_callers == {"services/command_center_service.py"}
    assert COMMAND_CENTER_OWNER.exists()
