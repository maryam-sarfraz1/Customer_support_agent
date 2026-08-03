"""Custom middleware: request logging and simple in-memory rate limiting."""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("app.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        started = time.monotonic()
        response = await call_next(request)
        elapsed_ms = int((time.monotonic() - started) * 1000)
        logger.info(
            "%s %s -> %d (%dms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window per-client rate limit.

    In-memory only — use an API gateway or Redis-backed limiter when running
    multiple replicas.
    """

    def __init__(self, app, limit_per_minute: int = 60) -> None:
        super().__init__(app)
        self._limit = limit_per_minute
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if request.url.path in ("/health", "/docs", "/openapi.json"):
            return await call_next(request)
        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = self._hits[client]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= self._limit:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": {
                        "code": "rate_limited",
                        "message": "Too many requests; please retry later.",
                    }
                },
            )
        window.append(now)
        return await call_next(request)
