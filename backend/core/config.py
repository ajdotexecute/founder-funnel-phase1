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

    class Config:
        env_file = str(_ENV_FILE)
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
