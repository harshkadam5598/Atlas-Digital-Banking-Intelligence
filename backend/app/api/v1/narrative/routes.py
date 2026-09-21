"""Atlas – Narrative Intelligence API. See narrative_service.py for logic."""

from __future__ import annotations

from datetime import date
from typing import Optional

from backend.app.api.v1.base import make_hub_router
from backend.app.core.exceptions import InvalidParameterError
from backend.app.schemas.envelope import envelope
from backend.app.services import narrative_service

router = make_hub_router(prefix="/narrative", tag="Narrative")
_VALID_CATEGORIES = ("all", "risk", "opportunity")


@router.get("/briefing", summary="Executive briefing digest")
def get_briefing(max_insights: int = 5, max_recommendations: int = 5, as_of: Optional[date] = None) -> dict:
    if not (1 <= max_insights <= 20):
        raise InvalidParameterError("max_insights must be between 1 and 20")
    if not (1 <= max_recommendations <= 20):
        raise InvalidParameterError("max_recommendations must be between 1 and 20")
    data = narrative_service.get_briefing(max_insights=max_insights, max_recommendations=max_recommendations, as_of=as_of)
    return envelope(data, as_of_date=as_of.isoformat() if as_of else None)


@router.get("/insights", summary="Executive insights, optionally filtered")
def get_insights(category: str = "all", max_insights: int = 10, as_of: Optional[date] = None) -> dict:
    if category not in _VALID_CATEGORIES:
        raise InvalidParameterError(f"category must be one of {_VALID_CATEGORIES}, got '{category}'")
    if not (1 <= max_insights <= 27):
        raise InvalidParameterError("max_insights must be between 1 and 27")
    data = narrative_service.get_insights(category=category, max_insights=max_insights, as_of=as_of)
    return envelope(data, as_of_date=as_of.isoformat() if as_of else None)


@router.get("/risk-summary", summary="Combined risk view: insights, anomalies, recommendations")
def get_risk_summary(as_of: Optional[date] = None) -> dict:
    data = narrative_service.get_risk_summary(as_of=as_of)
    return envelope(data, as_of_date=as_of.isoformat() if as_of else None)
