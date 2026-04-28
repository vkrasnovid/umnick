from __future__ import annotations

"""
Middleware: rate limiting and admin auth.
"""

import time
from collections import defaultdict
from typing import Callable

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from config import settings
from logging_setup import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter (100 req/min per tenant)."""

    def __init__(self, max_requests: int = 100, window: int = 60):
        self.max_requests = max_requests
        self.window = window
        self.requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        self.requests[key] = [t for t in self.requests[key] if now - t < self.window]
        if len(self.requests[key]) >= self.max_requests:
            return False
        self.requests[key].append(now)
        return True

    def cleanup(self) -> None:
        now = time.time()
        for key in list(self.requests.keys()):
            self.requests[key] = [t for t in self.requests[key] if now - t < self.window]
            if not self.requests[key]:
                del self.requests[key]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting per tenant via X-Tenant-Id header."""

    def __init__(self, app: Callable, max_requests: int = 100, window: int = 60):
        super().__init__(app)
        self.limiter = RateLimiter(max_requests=max_requests, window=window)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        tenant_id = request.headers.get("X-Tenant-Id", "anonymous")
        key = f"rate:{tenant_id}"

        if not self.limiter.is_allowed(key):
            logger.warning("Rate limit exceeded", tenant_id=tenant_id, path=request.url.path)
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again later.",
            )

        response = await call_next(request)
        return response


def verify_admin_token(request: Request) -> None:
    """Проверка X-Admin-Token для admin endpoints.

    Используется как FastAPI dependency.
    """
    admin_token = request.headers.get("X-Admin-Token", "")
    expected = settings.secret_key

    if not expected:
        logger.warning("Admin auth: SECRET_KEY is empty, skipping token check")
        return

    if admin_token != expected:
        logger.warning("Admin auth: invalid token", path=request.url.path)
        raise HTTPException(
            status_code=403,
            detail="Forbidden: invalid or missing admin token",
        )
