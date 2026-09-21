"""
Atlas – Product Intelligence API

Implements the Sprint 6 Product Intelligence capabilities:
    GET /product/summary
    GET /product/kpis
    GET /product/kpis/{name}
    GET /product/adoption
    GET /product/stickiness
    GET /product/cross-sell
    GET /product/feature-adoption

All business logic stays in analytics/kpis/product_kpis.py and
backend/app/services/product_service.py. All 4 registered product-
domain KPIs map directly onto the requested capabilities — no
analytics gap, no new KPI was needed.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from backend.app.api.v1.base import make_hub_router
from backend.app.schemas.envelope import envelope
from backend.app.services import product_service
from backend.app.utils.kpi_lookup import compute_in_domain

router = make_hub_router(prefix="/product", tag="Product")


@router.get("/summary", summary="Product intelligence summary")
def get_summary(as_of: Optional[date] = None) -> dict:
    data = product_service.get_summary(as_of=as_of)
    return envelope(data, as_of_date=data["as_of_date"])


@router.get("/kpis", summary="All product-domain KPIs")
def get_all_kpis(as_of: Optional[date] = None) -> dict:
    data = product_service.get_all_kpis(as_of=as_of)
    return envelope(data)


@router.get(
    "/kpis/{name}",
    summary="Single product-domain KPI by name",
    description=(
        "Generic lookup restricted to the product domain — a name "
        "registered under another domain 404s rather than silently "
        "computing it."
    ),
)
def get_kpi_by_name(name: str, as_of: Optional[date] = None) -> dict:
    result = compute_in_domain(name, "product", as_of=as_of)
    return envelope(result.to_dict(), as_of_date=result.as_of.isoformat())


@router.get("/adoption", summary="Product adoption rate per product")
def get_adoption(as_of: Optional[date] = None) -> dict:
    data = product_service.get_adoption(as_of=as_of)
    return envelope(data, as_of_date=data["as_of"])


@router.get("/stickiness", summary="Product stickiness (DAU/MAU) per product")
def get_stickiness(as_of: Optional[date] = None) -> dict:
    data = product_service.get_stickiness(as_of=as_of)
    return envelope(data, as_of_date=data["as_of"])


@router.get("/cross-sell", summary="Cross-sell rate (>=2 products held)")
def get_cross_sell(as_of: Optional[date] = None) -> dict:
    data = product_service.get_cross_sell(as_of=as_of)
    return envelope(data, as_of_date=data["as_of"])


@router.get(
    "/feature-adoption",
    summary="Feature penetration rate for a specific feature event",
    description=(
        "`feature_event_type` maps directly to "
        "fact_product_events.event_type (default 'premium_purchased'); "
        "pass e.g. 'crypto_activated' or 'investment_opened' for other "
        "features, per feature_adoption()'s existing parameter."
    ),
)
def get_feature_adoption(
    as_of: Optional[date] = None,
    feature_event_type: str = "premium_purchased",
) -> dict:
    data = product_service.get_feature_adoption(as_of=as_of, feature_event_type=feature_event_type)
    return envelope(data, as_of_date=data["as_of"])
