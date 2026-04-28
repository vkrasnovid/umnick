from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class EngineSettings(BaseSettings):
    database_url: str = "postgresql+asyncpg://umnick:umnick_pass@postgres:5432/umnick"
    database_url_sync: str = "postgresql://umnick:umnick_pass@postgres:5432/umnick"
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/0"
    openclaw_api_url: str = "http://openclaw:8080"
    openclaw_api_key: str = ""
    log_format: str = "json"
    log_level: str = "INFO"
    debug: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> EngineSettings:
    return EngineSettings()


settings = get_settings()
