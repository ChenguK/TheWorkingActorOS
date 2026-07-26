from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "The Working Actor OS API"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://casting:casting@localhost:5432/casting_intelligence"
    cors_origins: str = "http://localhost:5173"
    upload_dir: Path = Path("./storage/uploads")
    travel_provider: str = "manual"
    google_maps_api_key: str | None = None
    mapbox_access_token: str | None = None
    openrouteservice_api_key: str | None = None
    travel_cache_days: int = 30
    openai_api_key: str | None = None
    web_search_provider: str = "none"
    parallel_api_key: str | None = None
    scheduler_enabled: bool = False
    notifications_enabled: bool = False
    public_profile_import_enabled: bool = True
    supervised_browser_enabled: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def is_local_environment(self) -> bool:
        return self.environment.strip().lower() in {
            "development",
            "test",
            "testing",
            "contract_test",
        }

    @property
    def is_portfolio_demo(self) -> bool:
        return self.environment.strip().lower() == "portfolio_demo"

    @property
    def supervised_browser_available(self) -> bool:
        return self.is_local_environment and self.supervised_browser_enabled

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [
            origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()
        ]
        if not origins:
            raise ValueError("CORS_ORIGINS must contain at least one explicit frontend origin")
        for origin in origins:
            parsed = urlparse(origin)
            if origin == "*" or parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError(f"CORS_ORIGINS contains an invalid explicit origin: {origin!r}")
            if parsed.path not in {"", "/"} or parsed.params or parsed.query or parsed.fragment:
                raise ValueError(
                    f"CORS_ORIGINS must contain origins without paths or query strings: {origin!r}"
                )
            if not self.is_local_environment and parsed.hostname in {
                "localhost",
                "127.0.0.1",
                "::1",
            }:
                raise ValueError("Remote environments require a non-localhost CORS_ORIGINS value")
        return origins

    @model_validator(mode="after")
    def validate_portfolio_demo_posture(self) -> "Settings":
        if not self.is_portfolio_demo:
            return self
        enabled_external_configuration = [
            self.travel_provider.strip().lower() != "manual",
            bool(self.google_maps_api_key),
            bool(self.mapbox_access_token),
            bool(self.openrouteservice_api_key),
            bool(self.openai_api_key),
            self.web_search_provider.strip().lower() != "none",
            bool(self.parallel_api_key),
            self.scheduler_enabled,
            self.notifications_enabled,
            self.public_profile_import_enabled,
        ]
        if any(enabled_external_configuration):
            raise ValueError(
                "portfolio_demo requires external providers, scheduler, notifications, "
                "and public profile URL imports to remain disabled"
            )
        self.cors_origin_list
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
