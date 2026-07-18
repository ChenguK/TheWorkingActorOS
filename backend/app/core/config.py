from functools import lru_cache
from pathlib import Path

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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
