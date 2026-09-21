"""
Atlas – Customer Service

Orchestration layer for the Customer Intelligence API. Every number
traces to a real function in analytics/kpis/customer_kpis.py (or, for
value/segment metrics, revenue_kpis.py — see notes below). No new KPI
formulas are computed here.

Coverage against the Sprint 6 task's requested capabilities:
  - summary, kpis, individual KPI lookup -> direct registry exposure,
    customer domain (9 real KPIs).
  - retention, churn -> retention_rate() / churn_rate(), real, with
    retention's existing period_months parameter passed through.
  - CLV / customer value -> clv(), arpu(), ltv_cac_ratio(). These are
    registered under the "revenue" domain in registry.py (they live in
    revenue_kpis.py), not "customer" — but they are genuinely
    customer-value metrics and are exposed here via direct compute()
    calls, not duplicated. No new analytics needed.
  - segments -> genuine gap: no KPI computes a customer *count* or
    *composition* breakdown by segment. The closest existing real
    capability is revenue_kpis.revenue_by_segment (net revenue grouped
    by customer_segment). Exposed as-is with this documented instead of
    fabricating a customer-count-by-segment metric that doesn't exist
    in the Sprint 5 engine.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from analytics.kpis.registry import compute, compute_all

_SEGMENT_GAP_NOTE = (
    "No KPI computes customer count/composition by segment in the "
    "Sprint 5 analytics engine. revenue_by_segment (net revenue grouped "
    "by dim_customer.customer_segment) is the closest existing real "
    "capability and is exposed here as-is, not as a customer-count "
    "breakdown."
)


def get_summary(as_of: Optional[date] = None) -> dict:
    active = compute("active_customers", as_of=as_of)
    new = compute("new_customers", as_of=as_of)
    returning = compute("returning_customers", as_of=as_of)
    churn = compute("churn_rate", as_of=as_of)
    retention = compute("retention_rate", as_of=as_of)
    premium = compute("premium_conversion_rate", as_of=as_of)

    return {
        "active_customers": active.value,
        "new_customers": new.value,
        "returning_customers": returning.value,
        "churn_rate": churn.value,
        "retention_rate": retention.value,
        "premium_conversion_rate": premium.value,
        "as_of_date": active.as_of.isoformat(),
    }


def get_all_kpis(as_of: Optional[date] = None) -> dict:
    results = compute_all(as_of=as_of, domain="customer")
    return {
        "domain": "customer",
        "count": len(results),
        "kpis": {name: r.to_dict() for name, r in results.items()},
    }


def get_segments(as_of: Optional[date] = None) -> dict:
    result = compute("revenue_by_segment", as_of=as_of)
    data = result.to_dict()
    data["gap_note"] = _SEGMENT_GAP_NOTE
    return data


def get_retention(as_of: Optional[date] = None, period_months: int = 1) -> dict:
    result = compute("retention_rate", as_of=as_of, period_months=period_months)
    return result.to_dict()


def get_churn(as_of: Optional[date] = None) -> dict:
    result = compute("churn_rate", as_of=as_of)
    return result.to_dict()


def get_value(as_of: Optional[date] = None) -> dict:
    arpu = compute("arpu", as_of=as_of)
    clv = compute("clv", as_of=as_of)
    ltv_cac = compute("ltv_cac_ratio", as_of=as_of)
    return {
        "arpu": arpu.to_dict(),
        "clv": clv.to_dict(),
        "ltv_cac_ratio": ltv_cac.to_dict(),
        "as_of_date": arpu.as_of.isoformat(),
        "note": (
            "arpu/clv/ltv_cac_ratio are registered under the 'revenue' "
            "domain in registry.py (implemented in revenue_kpis.py) but "
            "are genuine per-customer value metrics — exposed here via "
            "direct registry calls, not duplicated."
        ),
    }
