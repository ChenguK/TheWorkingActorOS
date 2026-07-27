from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.supervised_breakdown_import_service import supervised_browser


pytestmark = pytest.mark.contract_smoke


def portfolio_settings(tmp_path) -> Settings:
    return Settings(
        _env_file=None,
        environment="portfolio_demo",
        database_url="supplied-by-contract-environment",
        cors_origins="https://portfolio.example.invalid",
        upload_dir=tmp_path / "uploads",
        durable_file_storage_enabled=False,
        travel_provider="manual",
        web_search_provider="none",
        scheduler_enabled=False,
        notifications_enabled=False,
        public_profile_import_enabled=False,
        supervised_browser_enabled=False,
    )


def test_clean_migrated_database_starts_with_sanitized_render_posture(tmp_path):
    settings = portfolio_settings(tmp_path)
    app = create_app(settings)

    with (
        patch("app.services.capability_service.get_settings", return_value=settings),
        patch("app.services.file_storage_service.get_settings", return_value=settings),
        patch.object(supervised_browser, "start") as browser_start,
        TestClient(app) as client,
    ):
        health = client.get("/health")
        capabilities = client.get("/api/v1/system/capabilities")
        allowed = client.options(
            "/health",
            headers={
                "Origin": "https://portfolio.example.invalid",
                "Access-Control-Request-Method": "GET",
            },
        )
        unconfigured = client.options(
            "/health",
            headers={
                "Origin": "https://unconfigured.example.invalid",
                "Access-Control-Request-Method": "GET",
            },
        )
        upload = client.post(
            "/api/v1/assets",
            data={
                "actor_profile_id": "00000000-0000-0000-0000-000000000001",
                "asset_name": "Disabled Demo Upload",
                "asset_type": "Headshot",
            },
            files={"file": ("demo.txt", b"sanitized", "text/plain")},
        )

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert capabilities.status_code == 200
    flags = capabilities.json()["flags"]
    assert flags["portfolio_demo"] is True
    assert flags["persistent_file_storage_available"] is False
    assert flags["supervised_browser_available"] is False
    assert allowed.headers["access-control-allow-origin"] == "https://portfolio.example.invalid"
    assert "access-control-allow-origin" not in unconfigured.headers
    assert upload.status_code == 503
    assert upload.json()["detail"]["code"] == "persistent_file_storage_unavailable"
    assert not settings.upload_dir.exists()
    browser_start.assert_not_called()
