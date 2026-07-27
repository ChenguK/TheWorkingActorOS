from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
RENDER_BLUEPRINT = ROOT / "render.yaml"
REQUIREMENTS = ROOT / "backend/requirements.txt"


def test_render_blueprint_defines_only_the_sanitized_backend_service():
    blueprint = yaml.safe_load(RENDER_BLUEPRINT.read_text())

    assert set(blueprint) == {"services"}
    assert len(blueprint["services"]) == 1
    service = blueprint["services"][0]
    assert service == {
        "type": "web",
        "name": "working-actor-os-api",
        "runtime": "python",
        "plan": "starter",
        "rootDir": "backend",
        "branch": "release/portfolio-readiness",
        "autoDeployTrigger": "checksPass",
        "buildCommand": "python -m pip install -r requirements.txt",
        "preDeployCommand": "python -m alembic upgrade head",
        "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT",
        "healthCheckPath": "/health",
        "envVars": service["envVars"],
    }

    env = {item["key"]: item for item in service["envVars"]}
    assert env["DATABASE_URL"] == {"key": "DATABASE_URL", "sync": False}
    assert env["CORS_ORIGINS"] == {"key": "CORS_ORIGINS", "sync": False}
    assert env["PYTHON_VERSION"]["value"] == "3.12.13"
    assert env["ENVIRONMENT"]["value"] == "portfolio_demo"
    assert env["DURABLE_FILE_STORAGE_ENABLED"]["value"] == "false"
    assert env["TRAVEL_PROVIDER"]["value"] == "manual"
    assert env["WEB_SEARCH_PROVIDER"]["value"] == "none"
    for key in (
        "SCHEDULER_ENABLED",
        "NOTIFICATIONS_ENABLED",
        "PUBLIC_PROFILE_IMPORT_ENABLED",
        "SUPERVISED_BROWSER_ENABLED",
    ):
        assert env[key]["value"] == "false"
    for key in (
        "OPENAI_API_KEY",
        "PARALLEL_API_KEY",
        "GOOGLE_MAPS_API_KEY",
        "MAPBOX_ACCESS_TOKEN",
        "OPENROUTESERVICE_API_KEY",
    ):
        assert env[key]["value"] == ""


def test_render_production_requirements_are_fully_pinned():
    lines = [
        line.strip()
        for line in REQUIREMENTS.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]

    assert lines
    assert all("==" in line for line in lines)
    assert any(line.startswith("fastapi==") for line in lines)
    assert any(line.startswith("uvicorn==") for line in lines)
    assert any(line.startswith("alembic==") for line in lines)
    assert not any(line.startswith(("pytest==", "ruff==")) for line in lines)
