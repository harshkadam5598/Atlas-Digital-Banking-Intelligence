"""
Atlas – API Response Envelope

Every /api/v1/* endpoint returns this exact shape, per the stable
contract defined in frontend/contracts/api_contracts.md:

    { "data": <payload|null>, "meta": {...}, "errors": [...]|null }

This module is the single place that shape is defined. Route handlers
never construct the envelope by hand — they return a payload (dict,
list, or a dataclass with .to_dict()) via `envelope()`, or raise an
AtlasAPIError and let the exception handler build the error envelope.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ResponseMeta(BaseModel):
    """Metadata attached to every successful response."""

    as_of_date: Optional[str] = None
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    cached: bool = False
    cache_ttl_seconds: Optional[int] = None


class ErrorDetail(BaseModel):
    """A single error entry. Multiple can be returned (e.g. validation)."""

    code: str
    message: str


class Envelope(BaseModel, Generic[T]):
    """Generic envelope — used directly, or subclassed for OpenAPI clarity."""

    data: Optional[T] = None
    meta: Optional[ResponseMeta] = None
    errors: Optional[List[ErrorDetail]] = None


def envelope(
    data: Any,
    *,
    as_of_date: Optional[str] = None,
    cached: bool = False,
    cache_ttl_seconds: Optional[int] = None,
) -> dict:
    """
    Build a successful response envelope as a plain dict.

    `data` may be:
      - a dict/list already in serialisable form
      - any object exposing `.to_dict()` (KPIResult, Insight, Recommendation,
        ForecastResult, Anomaly — all analytics engine outputs already do)
      - a list of such objects, which is unwrapped element-by-element

    Route handlers should not build this dict by hand — always go through
    this function so the envelope shape stays consistent across all 8 hubs.
    """
    return {
        "data": _serialise(data),
        "meta": ResponseMeta(
            as_of_date=as_of_date,
            cached=cached,
            cache_ttl_seconds=cache_ttl_seconds,
        ).model_dump(),
        "errors": None,
    }


def _serialise(data: Any) -> Any:
    if data is None:
        return None
    if isinstance(data, list):
        return [_serialise(item) for item in data]
    if isinstance(data, dict):
        return data
    to_dict = getattr(data, "to_dict", None)
    if callable(to_dict):
        return to_dict()
    return data
