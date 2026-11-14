from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

API_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """App settings, read from environment variables or a local .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    cors_origins: list[str] = ["http://localhost:3000"]
    tax_profiles_path: Path = API_ROOT / "config" / "tax_profiles.yaml"

    supabase_url: str = ""
    supabase_service_role_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
