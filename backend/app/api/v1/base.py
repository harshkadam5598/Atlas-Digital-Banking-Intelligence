"""
Atlas – Hub Router Foundation

Every intelligence-hub router is built the same way: an APIRouter
guarded by the shared API-key dependency, tagged for the OpenAPI docs.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.core.security import require_api_key


def make_hub_router(*, prefix: str, tag: str) -> APIRouter:
    return APIRouter(
        prefix=prefix,
        tags=[tag],
        dependencies=[Depends(require_api_key)],
    )
