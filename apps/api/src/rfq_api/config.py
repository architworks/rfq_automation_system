from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "RFQ Rubric API"
    api_prefix: str = ""
    frontend_origin: str = "http://localhost:3000"
    session_ttl_seconds: int = 60 * 60 * 2

    azure_openai_endpoint: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_model: str | None = Field(default=None)
    azure_openai_timeout_seconds: float = 60.0


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
