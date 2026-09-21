"""
Atlas KPI Engine — Product Domain

Product Adoption, Product Stickiness (DAU/MAU), Cross-sell Rate,
Feature Adoption. Formulas trace to docs/business/kpi_definitions.md
Module 4 (Product Intelligence).
"""

from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd

from analytics.core.data_context import DataContext, get_data_context
from analytics.core.types import KPIResult
from analytics.kpis.periods import month_bounds, safe_ratio


def _resolve(ctx: Optional[DataContext], as_of: Optional[date]):
    ctx = ctx or get_data_context()
    as_of = as_of or ctx.as_of()
    return ctx, as_of


def product_adoption(ctx: Optional[DataContext] = None,
                     as_of: Optional[date] = None) -> KPIResult:
    """
    Product Adoption Rate per product:
    COUNT(DISTINCT customer with >=1 event for product P) / COUNT(active_customers) x 100
    """
    ctx, as_of = _resolve(ctx, as_of)
    evt = ctx.get("fact_product_events")
    cust = ctx.get("dim_customer")

    active_base = len(cust[cust["lifecycle_stage"].isin(
        {"activated", "reactivated", "churned"})]) if len(cust) else 0

    if not len(evt) or active_base == 0:
        return KPIResult(name="product_adoption", value=0.0, unit="percent", as_of=as_of)

    adopters_by_product = evt.groupby("product_code")["customer_id"].nunique()
    rate_by_product = (adopters_by_product / active_base * 100).round(2)

    overall_adopters = evt["customer_id"].nunique()
    overall_rate = round(safe_ratio(overall_adopters, active_base) * 100, 2)

    return KPIResult(
        name="product_adoption", value=overall_rate, unit="percent",
        as_of=as_of, period_label=as_of.isoformat(),
        metadata={"active_customer_base": active_base},
        breakdown={"by_product": rate_by_product.to_dict()},
    )


def product_stickiness(ctx: Optional[DataContext] = None,
                       as_of: Optional[date] = None) -> KPIResult:
    """
    Product Stickiness (DAU/MAU) per product.
    Benchmark: >0.20 sticky, >0.50 highly sticky (kpi_definitions.md).
    Returns the platform-wide blended ratio as headline value, with
    per-product ratios in breakdown.
    """
    ctx, as_of = _resolve(ctx, as_of)
    evt = ctx.get("fact_product_events")
    if not len(evt):
        return KPIResult(name="product_stickiness", value=0.0, unit="ratio", as_of=as_of)

    month_start, month_end = month_bounds(as_of)
    month_evt = evt[evt["event_date"].dt.date.between(month_start, month_end)]
    day_evt = evt[evt["event_date"].dt.date == as_of]

    if not len(month_evt):
        return KPIResult(name="product_stickiness", value=0.0, unit="ratio", as_of=as_of)

    mau_by_product = month_evt.groupby("product_code")["customer_id"].nunique()
    dau_by_product = day_evt.groupby("product_code")["customer_id"].nunique()

    ratios = {}
    for product in mau_by_product.index:
        dau = int(dau_by_product.get(product, 0))
        mau = int(mau_by_product[product])
        ratios[product] = round(safe_ratio(dau, mau), 3)

    overall_dau = day_evt["customer_id"].nunique()
    overall_mau = month_evt["customer_id"].nunique()
    overall_ratio = round(safe_ratio(overall_dau, overall_mau), 3)

    return KPIResult(
        name="product_stickiness", value=overall_ratio, unit="ratio",
        as_of=as_of, period_label=month_start.strftime("%Y-%m"),
        metadata={"benchmark": "sticky >0.20, highly_sticky >0.50"},
        breakdown={"by_product": ratios},
    )


def cross_sell_rate(ctx: Optional[DataContext] = None,
                    as_of: Optional[date] = None) -> KPIResult:
    """Cross-sell Rate: % of active customers holding >= 2 distinct products."""
    ctx, as_of = _resolve(ctx, as_of)
    cust = ctx.get("dim_customer")
    if not len(cust):
        return KPIResult(name="cross_sell_rate", value=0.0, unit="percent", as_of=as_of)

    active = cust[cust["lifecycle_stage"].isin({"activated", "reactivated"})]
    if not len(active):
        return KPIResult(name="cross_sell_rate", value=0.0, unit="percent", as_of=as_of)

    multi_product = active[active["product_count"] >= 2]
    rate = round(safe_ratio(len(multi_product), len(active)) * 100, 2)

    distribution = active["product_count"].value_counts().sort_index().to_dict()

    return KPIResult(
        name="cross_sell_rate", value=rate, unit="percent",
        as_of=as_of, period_label=as_of.isoformat(),
        metadata={"active_base": len(active), "multi_product_count": len(multi_product)},
        breakdown={"product_count_distribution": {str(k): v for k, v in distribution.items()}},
    )


def feature_adoption(ctx: Optional[DataContext] = None,
                     as_of: Optional[date] = None,
                     feature_event_type: str = "premium_purchased") -> KPIResult:
    """
    Feature Penetration Rate: % of eligible customers who have used a
    specific feature (identified by fact_product_events.event_type).
    Default feature is premium_purchased; callers pass other event_types
    (e.g. "crypto_activated", "investment_opened") for other features.
    """
    ctx, as_of = _resolve(ctx, as_of)
    evt = ctx.get("fact_product_events")
    cust = ctx.get("dim_customer")

    eligible_base = len(cust[cust["lifecycle_stage"].isin(
        {"activated", "reactivated", "churned"})]) if len(cust) else 0

    if not len(evt) or eligible_base == 0:
        return KPIResult(name="feature_adoption", value=0.0, unit="percent", as_of=as_of)

    feature_users = evt[evt["event_type"] == feature_event_type]["customer_id"].nunique()
    rate = round(safe_ratio(feature_users, eligible_base) * 100, 2)

    return KPIResult(
        name="feature_adoption", value=rate, unit="percent",
        as_of=as_of, period_label=as_of.isoformat(),
        metadata={
            "feature_event_type": feature_event_type,
            "feature_users": feature_users,
            "eligible_base": eligible_base,
        },
    )
