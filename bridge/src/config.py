from __future__ import annotations

import os
from typing import ClassVar

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://umnick:umnick_pass@postgres:5432/umnick"
    database_url_sync: str = "postgresql://umnick:umnick_pass@postgres:5432/umnick"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Celery
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/0"

    # Encryption
    encryption_key: str = ""

    # OpenClaw
    openclaw_api_url: str = "http://openclaw:8080"
    openclaw_api_key: str = ""

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    debug: bool = False

    # App
    secret_key: str = os.getenv("SECRET_KEY", "")
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # OpenTelemetry
    otel_service_name: str = "umnick"
    otel_exporter_otlp_endpoint: str = "http://otel-collector:4318"

    model_config: ClassVar = {"env_file": ".env", "env_file_encoding": "utf-8"}

    def model_post_init(self, __context):
        if not self.secret_key:
            raise ValueError("SECRET_KEY environment variable is required")


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
