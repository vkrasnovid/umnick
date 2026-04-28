from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class ToolsSettings(BaseSettings):
    database_url: str = "postgresql+asyncpg://umnick:umnick_pass@postgres:5432/umnick"
    log_level: str = "INFO"
    debug: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> ToolsSettings:
    return ToolsSettings()


settings = get_settings()
