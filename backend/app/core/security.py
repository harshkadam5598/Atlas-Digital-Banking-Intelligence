"""
Atlas – API Security (Sprint 6: lightweight guard)

A single static credential checked via the `X-API-Key` header. This is
intentionally NOT full JWT authentication — there is no user/session
model anywhere in Atlas to justify one yet. JWTSettings (core/config.py)
already models secret/algorithm/token-expiry and is reserved for that
build-out in a later infrastructure sprint; this module exists so
Sprint 6's routers aren't left completely unauthenticated in the
meantime.
"""

from __future__ import annotations

from fastapi import Header
from fastapi.security import APIKeyHeader

from backend.app.core.config import settings
from backend.app.core.exceptions import UnauthorizedError

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    if not settings.api_key_enabled:
        return
    if x_api_key is None or x_api_key != settings.api_key:
        raise UnauthorizedError("Missing or invalid X-API-Key header.")
