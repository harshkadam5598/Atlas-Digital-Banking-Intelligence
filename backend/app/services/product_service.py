"""
Atlas – Product Service

Orchestration layer for the Product Intelligence API. Every number
traces to a real function in analytics/kpis/product_kpis.py. No new
formulas are computed here.

Coverage against the Sprint 6 task's requested capabilities: summary,
kpis, individual lookup, adoption, stickiness, cross-sell, feature
adoption — all 4 registered product-domain KPIs cover exactly this
list, so no analytics gap and no new KPI was needed for Product.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from analytics.kpis.registry import compute, compute_all


def get_summary(as_of: Optional[date] = None) -> dict:
    adoption = compute("product_adoption", as_of=as_of)
    stickiness = compute("product_stickiness", as_of=as_of)
    cross_sell = compute("cross_sell_rate", as_of=as_of)

    return {
        "product_adoption": adoption.value,
        "product_stickiness": stickiness.value,
        "cross_sell_rate": cross_sell.value,
        "as_of_date": adoption.as_of.isoformat(),
    }


def get_all_kpis(as_of: Optional[date] = None) -> dict:
    results = compute_all(as_of=as_of, domain="product")
    return {
        "domain": "product",
        "count": len(results),
        "kpis": {name: r.to_dict() for name, r in results.items()},
    }


def get_adoption(as_of: Optional[date] = None) -> dict:
    return compute("product_adoption", as_of=as_of).to_dict()


def get_stickiness(as_of: Optional[date] = None) -> dict:
    return compute("product_stickiness", as_of=as_of).to_dict()


def get_cross_sell(as_of: Optional[date] = None) -> dict:
    return compute("cross_sell_rate", as_of=as_of).to_dict()


def get_feature_adoption(as_of: Optional[date] = None,
                         feature_event_type: str = "premium_purchased") -> dict:
    return compute(
        "feature_adoption", as_of=as_of, feature_event_type=feature_event_type
    ).to_dict()
