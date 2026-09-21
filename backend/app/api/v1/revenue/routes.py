"""Atlas – Revenue Intelligence Hub API. See revenue_service.py for logic."""

from __future__ import annotations

from datetime import date
from typing import Optional

from backend.app.api.v1.base import make_hub_router
from backend.app.schemas.envelope import envelope
from backend.app.services import revenue_service
from backend.app.utils.params import validate_date_range, validate_granularity

router = make_hub_router(prefix="/revenue", tag="Revenue")


@router.get("/summary", summary="Revenue breakdown by type")
def get_revenue_summary(start_date: Optional[date] = None, end_date: Optional[date] = None) -> dict:
    validate_date_range(start_date, end_date)
    data = revenue_service.get_revenue_summary(start_date, end_date)
    return envelope(data, as_of_date=data["as_of"])


@router.get("/trend", summary="Revenue time-series")
def get_revenue_trend(granularity: str = "month") -> dict:
    validate_granularity(granularity)
    data = revenue_service.get_revenue_trend(granularity)
    return envelope(data)


@router.get("/forecast", summary="Revenue forecast")
def get_revenue_forecast() -> dict:
    data = revenue_service.get_revenue_forecast()
    return envelope(data)
