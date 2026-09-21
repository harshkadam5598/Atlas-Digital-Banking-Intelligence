"""
Atlas – Market Intelligence API

Implements the four Sprint 6 Market endpoints:
    GET /market/summary
    GET /market/geographic
    GET /market/anomalies
    GET /market/efficiency

All business logic stays in analytics/kpis/revenue_kpis.py,
analytics/kpis/customer_kpis.py, and
analytics/anomaly/anomaly_engine.py — this module only validates
request params, calls backend/app/services/market_service.py, and
wraps the result in the standard envelope. No new KPI was added and
registry.py was not modified for Market. See market_service.py's
module docstring for the documented derivation of the two Module 7
formulas and the /market/efficiency proxy caveat.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from backend.app.api.v1.base import make_hub_router
from backend.app.schemas.envelope import envelope
from backend.app.services import market_service

router = make_hub_router(prefix="/market", tag="Market")


@router.get("/summary", summary="Market intelligence summary")
def get_summary(as_of: Optional[date] = None) -> dict:
    data = market_service.get_summary(as_of=as_of)
    return envelope(data, as_of_date=data["as_of_date"])


@router.get(
    "/geographic",
    summary="Geographic revenue and customer-growth intelligence",
    description=(
        "Real revenue_by_country() output, plus two figures derived "
        "per docs/business/kpi_definitions.md Module 7 — Geographic "
        "Revenue Contribution % and Country Customer Growth Rate MoM. "
        "Both are plain arithmetic on existing function outputs "
        "(revenue_by_country, two new_customers() calls), not new KPI "
        "logic. See `note` in the response."
    ),
)
def get_geographic(as_of: Optional[date] = None) -> dict:
    data = market_service.get_geographic(as_of=as_of)
    return envelope(data, as_of_date=data["as_of_date"])


@router.get(
    "/anomalies",
    summary="Country-level revenue anomalies",
    description=(
        "Sourced directly from "
        "analytics.anomaly.anomaly_engine.detect_country_anomalies() — "
        "each country compared only to its own trailing history."
    ),
)
def get_anomalies() -> dict:
    data = market_service.get_anomalies()
    return envelope(data)


@router.get(
    "/efficiency",
    summary="Acquisition-efficiency proxy (LTV/CAC)",
    description=(
        "Atlas has no formally defined 'Market Efficiency' KPI — this "
        "endpoint exposes ltv_cac_ratio as the closest available "
        "acquisition-efficiency proxy. See `proxy_note` in the "
        "response; do not treat this as an official Market Efficiency "
        "metric."
    ),
)
def get_efficiency(as_of: Optional[date] = None) -> dict:
    data = market_service.get_efficiency(as_of=as_of)
    return envelope(data, as_of_date=data["as_of"])
