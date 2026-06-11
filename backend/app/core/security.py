from __future__ import annotations

import json
from collections import defaultdict, deque
from time import monotonic
from typing import Deque, Dict, Tuple


class RateLimitMiddleware:
    """Small in-process per-IP limiter for the MVP API.

    Nginx still sits in front of the app, but this keeps expensive map and
    analysis endpoints from being hammered if proxy rules are changed later.
    """

    def __init__(
        self,
        app,
        *,
        default_requests_per_minute: int,
        expensive_requests_per_minute: int,
        window_seconds: int = 60,
    ) -> None:
        self.app = app
        self.default_limit = max(1, default_requests_per_minute)
        self.expensive_limit = max(1, expensive_requests_per_minute)
        self.window_seconds = max(1, window_seconds)
        self._hits: Dict[Tuple[str, str], Deque[float]] = defaultdict(deque)

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if not path.startswith("/api/") or path == "/api/health":
            await self.app(scope, receive, send)
            return

        client_ip = _client_ip(scope)
        bucket = _bucket_for_path(path)
        limit = self.expensive_limit if bucket == "expensive" else self.default_limit

        now = monotonic()
        key = (client_ip, bucket)
        hits = self._hits[key]
        cutoff = now - self.window_seconds
        while hits and hits[0] < cutoff:
            hits.popleft()

        if len(hits) >= limit:
            retry_after = max(1, int(self.window_seconds - (now - hits[0])))
            body = json.dumps(
                {
                    "detail": "Too many requests. Please retry later.",
                    "retry_after_seconds": retry_after,
                }
            ).encode("utf-8")
            await send(
                {
                    "type": "http.response.start",
                    "status": 429,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"retry-after", str(retry_after).encode("ascii")),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return

        hits.append(now)
        await self.app(scope, receive, send)


def _bucket_for_path(path: str) -> str:
    if path in {"/api/analysis", "/api/pois/search", "/api/map/search", "/api/map/geocode"}:
        return "expensive"
    return "default"


def _client_ip(scope) -> str:
    headers = {key.lower(): value for key, value in scope.get("headers", [])}
    forwarded_for = headers.get(b"x-forwarded-for")
    if forwarded_for:
        return forwarded_for.decode("latin1", errors="ignore").split(",", 1)[0].strip() or "unknown"
    client = scope.get("client")
    if client:
        return str(client[0])
    return "unknown"
