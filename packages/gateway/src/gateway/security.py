from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from gateway.config import Settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy",
            "accelerometer=(), camera=(), geolocation=(), microphone=()",
        )
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains",
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object, *, settings: Settings) -> None:
        super().__init__(app)
        self._settings = settings
        self._hits: dict[str, list[float]] = defaultdict(list)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        rpm = self._settings.rate_limit_rpm
        if rpm <= 0 or not request.url.path.startswith("/v1/"):
            return await call_next(request)

        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = [t for t in self._hits[client] if now - t < 60.0]
        if len(window) >= rpm:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "rate_limit_exceeded",
                        "message": "Too many requests; try again later",
                    }
                },
                headers={"Retry-After": "60"},
            )
        window.append(now)
        self._hits[client] = window
        return await call_next(request)
