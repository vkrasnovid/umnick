from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """Liveness probe."""
    return {"status": "ok", "service": "bridge"}


@router.get("/ready")
async def readiness(db: AsyncSession = Depends(get_session)):
    """Readiness probe — проверяет соединение с БД и Redis."""
    import redis.asyncio as aioredis
    from config import settings

    try:
        await db.execute(sa_text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    try:
        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        redis_ok = True
    except Exception:
        redis_ok = False

    if db_ok and redis_ok:
        return {"status": "ready", "database": "ok", "redis": "ok"}
    elif db_ok:
        return {"status": "degraded", "database": "ok", "redis": "down"}
    else:
        return {"status": "not_ready", "database": "down", "redis": "ok" if redis_ok else "down"}
