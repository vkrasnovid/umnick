from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from logging_setup import setup_logging, get_logger
from middleware import RateLimitMiddleware
from web.routers import health, admin

setup_logging("umnick-bridge")
logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Создать FastAPI приложение."""
    app = FastAPI(
        title="Умник — Data Bridge",
        description="AI Operations Platform — Data Integration & Storage",
        version="1.0.0",
    )

    # CORS
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate limiting (per tenant)
    app.add_middleware(RateLimitMiddleware, max_requests=100, window=60)

    # Routers
    app.include_router(health.router)
    app.include_router(admin.router)

    @app.on_event("startup")
    async def startup():
        logger.info("Bridge service starting", version="1.0.0")

    @app.on_event("shutdown")
    async def shutdown():
        from database import engine
        await engine.dispose()
        logger.info("Bridge service stopped")

    return app


app = create_app()
