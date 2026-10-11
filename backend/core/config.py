from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    app_name: str = "Founder Funnel"
    app_version: str = "0.1.0"

    database_url: str = "postgresql+asyncpg://founder:founder_pass@localhost:5432/founder_funnel"

    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 20

    max_calculator_attempts: int = 3

    # "local" | "box" (box lands in Checkpoint 5 — see services/storage.py)
    storage_backend: str = "local"

    # Unset -> neutral demo config/theme, per the amended hard constraints.
    client_id: str = "demo"

    anthropic_api_key: str = ""
    ai_model: str = "claude-sonnet-5-5"
    ai_timeout_seconds: float = 60.0
    ai_max_retries: int = 2

    companies_house_api_key: str = ""
    companies_house_base_url: str = "https://api.company-information.service.gov.uk"

    class Config:
        env_file = str(_ENV_FILE)
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
