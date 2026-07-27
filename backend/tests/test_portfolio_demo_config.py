from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from app.api.v1.routes.supervised_breakdowns import (
    close_supervised_browser,
    import_current_supervised_page,
    start_supervised_browser,
    supervised_browser_status,
)
from app.core.config import Settings
from app.main import create_app
from app.schemas.supervised_breakdown import SupervisedBrowserStart
from app.services.capability_service import CapabilityService
from app.services.supervised_breakdown_import_service import (
    SupervisedBreakdownImportService,
    supervised_browser,
)


def local_settings(**overrides) -> Settings:
    values = {
        "environment": "development",
        "cors_origins": "http://localhost:5173,http://127.0.0.1:5173",
        **overrides,
    }
    return Settings(_env_file=None, **values)


def portfolio_settings(**overrides) -> Settings:
    values = {
        "environment": "portfolio_demo",
        "cors_origins": "https://portfolio.example.invalid",
        "public_profile_import_enabled": False,
        "supervised_browser_enabled": False,
        **overrides,
    }
    return Settings(_env_file=None, **values)


def test_local_mode_keeps_supervised_browser_available():
    settings = local_settings()
    service = SupervisedBreakdownImportService(MagicMock())

    with (
        patch(
            "app.services.supervised_breakdown_import_service.get_settings",
            return_value=settings,
        ),
        patch.object(supervised_browser, "start", return_value={"active": True}) as start,
    ):
        assert service.start_browser("Actors Access") == {"active": True}

    start.assert_called_once_with("Actors Access")
    assert settings.persistent_file_storage_available is True


def test_remote_file_storage_requires_explicit_durable_configuration():
    assert portfolio_settings().persistent_file_storage_available is False
    assert (
        portfolio_settings(durable_file_storage_enabled=True).persistent_file_storage_available
        is True
    )
    assert (
        local_settings(durable_file_storage_enabled=False).persistent_file_storage_available
        is False
    )


def test_portfolio_mode_disables_browser_operations_without_touching_playwright():
    settings = portfolio_settings()
    service = SupervisedBreakdownImportService(MagicMock())

    with (
        patch(
            "app.services.supervised_breakdown_import_service.get_settings",
            return_value=settings,
        ),
        patch.object(supervised_browser, "start") as start,
        patch.object(supervised_browser, "capture_visible_page") as capture,
        patch.object(supervised_browser, "close") as close,
    ):
        with pytest.raises(RuntimeError, match="sanitized portfolio demo"):
            service.start_browser("Actors Access")
        with pytest.raises(RuntimeError, match="sanitized portfolio demo"):
            service.import_current_page()
        status = service.browser_status()
        closed = service.close_browser()

    start.assert_not_called()
    capture.assert_not_called()
    close.assert_not_called()
    assert (
        status
        == closed
        == {
            "available": False,
            "active": False,
            "platform_name": None,
            "current_url": None,
            "message": (
                "Supervised browser automation is disabled in the sanitized portfolio demo. "
                "Use manual breakdown entry or paste the breakdown text instead."
            ),
        }
    )


def test_disabled_routes_use_stable_status_and_response_shape():
    settings = portfolio_settings()
    db = MagicMock()

    with patch(
        "app.services.supervised_breakdown_import_service.get_settings",
        return_value=settings,
    ):
        with pytest.raises(HTTPException) as start_error:
            start_supervised_browser(
                SupervisedBrowserStart(platform_name="Actors Access"),
                db,
            )
        with pytest.raises(HTTPException) as capture_error:
            import_current_supervised_page(db)
        status = supervised_browser_status(db)
        closed = close_supervised_browser(db)

    for error in (start_error.value, capture_error.value):
        assert error.status_code == 503
        assert error.detail["code"] == "supervised_browser_disabled"
        assert "sanitized portfolio demo" in error.detail["message"]
    assert status["available"] is False
    assert status["active"] is False
    assert closed == status


def test_cors_uses_only_exact_configured_origins():
    settings = local_settings()
    app = create_app(settings)
    cors = next(
        middleware for middleware in app.user_middleware if middleware.cls is CORSMiddleware
    )

    assert cors.kwargs["allow_origins"] == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    assert "*" not in cors.kwargs["allow_origins"]


def test_remote_mode_rejects_wildcard_localhost_and_missing_origins():
    for origins in ("*", "http://localhost:5173", ""):
        with pytest.raises((ValidationError, ValueError)):
            portfolio_settings(cors_origins=origins)


def test_portfolio_mode_rejects_enabled_external_integrations():
    with pytest.raises(ValidationError, match="external providers"):
        portfolio_settings(openai_api_key="not-a-real-key")


def test_capability_output_matches_local_and_portfolio_route_behavior():
    service = CapabilityService(MagicMock())

    with (
        patch.object(service, "_source_discovery_configured", return_value=False),
        patch(
            "app.services.capability_service.TravelService.provider_status",
            return_value={"configured": False, "provider": "manual", "state": "Not Configured"},
        ),
        patch("app.services.capability_service.get_settings", return_value=local_settings()),
    ):
        local_flags = service.flags()
        local_integrations = service.integration_statuses(local_flags)

    with (
        patch.object(service, "_source_discovery_configured", return_value=False),
        patch(
            "app.services.capability_service.TravelService.provider_status",
            return_value={"configured": False, "provider": "manual", "state": "Not Configured"},
        ),
        patch("app.services.capability_service.get_settings", return_value=portfolio_settings()),
    ):
        portfolio_flags = service.flags()
        portfolio_integrations = service.integration_statuses(portfolio_flags)

    local_browser = next(item for item in local_integrations if item["id"] == "supervised_browser")
    portfolio_browser = next(
        item for item in portfolio_integrations if item["id"] == "supervised_browser"
    )
    assert local_flags["supervised_browser_available"] is True
    assert local_flags["portfolio_demo"] is False
    assert local_browser["status"] == "Available Locally"
    assert portfolio_flags["supervised_browser_available"] is False
    assert local_flags["persistent_file_storage_available"] is True
    assert portfolio_flags["persistent_file_storage_available"] is False
    assert portfolio_flags["portfolio_demo"] is True
    assert portfolio_browser["status"] == "Unavailable in Portfolio Demo"
    assert (
        portfolio_browser["fallback_behavior"] == "Manual breakdown entry or pasted breakdown text."
    )
    portfolio_storage = next(
        item for item in portfolio_integrations if item["id"] == "persistent_file_storage"
    )
    assert portfolio_storage["configured"] is False
    assert portfolio_storage["status"] == "Not Configured"


def test_local_configuration_can_explicitly_disable_supervised_browser():
    settings = local_settings(supervised_browser_enabled=False)
    service = SupervisedBreakdownImportService(MagicMock())

    with (
        patch(
            "app.services.supervised_breakdown_import_service.get_settings",
            return_value=settings,
        ),
        patch.object(supervised_browser, "start") as start,
    ):
        with pytest.raises(RuntimeError, match="SUPERVISED_BROWSER_ENABLED"):
            service.start_browser("Actors Access")

    start.assert_not_called()
    assert (
        CapabilityService(MagicMock())._supervised_browser_status(settings)
        == "Disabled by Configuration"
    )
