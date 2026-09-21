"""
Atlas – Customer Intelligence API

Implements the Sprint 6 Customer Intelligence capabilities:
    GET /customer/summary
    GET /customer/kpis
    GET /customer/kpis/{name}
    GET /customer/segments
    GET /customer/retention
    GET /customer/churn
    GET /customer/value

All business logic stays in analytics/kpis/ (customer_kpis.py and, for
value/segments, revenue_kpis.py via direct registry calls) and
backend/app/services/customer_service.py. See customer_service.py's
module docstring for the documented `segments` capability gap.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from backend.app.api.v1.base import make_hub_router
from backend.app.schemas.envelope import envelope
from backend.app.services import customer_service
from backend.app.utils.kpi_lookup import compute_in_domain

router = make_hub_router(prefix="/customer", tag="Customer")


@router.get("/summary", summary="Customer intelligence summary")
def get_summary(as_of: Optional[date] = None) -> dict:
    data = customer_service.get_summary(as_of=as_of)
    return envelope(data, as_of_date=data["as_of_date"])


@router.get("/kpis", summary="All customer-domain KPIs")
def get_all_kpis(as_of: Optional[date] = None) -> dict:
    data = customer_service.get_all_kpis(as_of=as_of)
    return envelope(data)


@router.get(
    "/kpis/{name}",
    summary="Single customer-domain KPI by name",
    description=(
        "Generic lookup restricted to the customer domain — a name "
        "registered under another domain (e.g. 'total_revenue') 404s "
        "rather than silently computing it."
    ),
)
def get_kpi_by_name(name: str, as_of: Optional[date] = None) -> dict:
    result = compute_in_domain(name, "customer", as_of=as_of)
    return envelope(result.to_dict(), as_of_date=result.as_of.isoformat())


@router.get(
    "/segments",
    summary="Segment breakdown",
    description=(
        "No customer-count-by-segment KPI exists in the Sprint 5 engine. "
        "Exposes the closest existing real capability — "
        "revenue_by_segment (net revenue grouped by customer_segment) — "
        "as-is. See `gap_note` in the response."
    ),
)
def get_segments(as_of: Optional[date] = None) -> dict:
    data = customer_service.get_segments(as_of=as_of)
    return envelope(data, as_of_date=data["as_of"])


@router.get("/retention", summary="Cohort retention rate")
def get_retention(as_of: Optional[date] = None, period_months: int = 1) -> dict:
    data = customer_service.get_retention(as_of=as_of, period_months=period_months)
    return envelope(data, as_of_date=data["as_of"])


@router.get("/churn", summary="Monthly churn rate")
def get_churn(as_of: Optional[date] = None) -> dict:
    data = customer_service.get_churn(as_of=as_of)
    return envelope(data, as_of_date=data["as_of"])


@router.get(
    "/value",
    summary="Customer value metrics: ARPU, CLV, LTV/CAC",
    description=(
        "arpu/clv/ltv_cac_ratio are registered under the registry's "
        "'revenue' domain (implemented in revenue_kpis.py) but are "
        "genuine per-customer value metrics, exposed here via direct "
        "registry calls — not duplicated logic."
    ),
)
def get_value(as_of: Optional[date] = None) -> dict:
    data = customer_service.get_value(as_of=as_of)
    return envelope(data, as_of_date=data["as_of_date"])
