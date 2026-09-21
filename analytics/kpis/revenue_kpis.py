"""
Atlas KPI Engine — Revenue Domain

Total Revenue, Revenue by Product, Revenue by Country, Revenue by Customer
Segment, ARPU, CLV, LTV/CAC, Revenue Growth.

Formulas trace to docs/business/kpi_definitions.md Module 5 (Revenue
Intelligence) and Module 2 (CLV).
"""

from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd
from loguru import logger

from analytics.core.data_context import DataContext, get_data_context
from analytics.core.types import KPIResult
from analytics.kpis.periods import month_bounds, previous_month_bounds, safe_pct_change, safe_ratio

GROSS_MARGIN_ASSUMPTION = 0.65  # kpi_definitions.md Module 2 — CLV formula


def _resolve(ctx: Optional[DataContext], as_of: Optional[date]):
    ctx = ctx or get_data_context()
    as_of = as_of or ctx.as_of()
    return ctx, as_of


def _month_revenue(rev: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    if not len(rev):
        return rev
    return rev[rev["revenue_date"].dt.date.between(start, end)]


# ── Total revenue & growth ───────────────────────────────────────────────────────

def total_revenue(ctx: Optional[DataContext] = None,
                  as_of: Optional[date] = None) -> KPIResult:
    """Total Revenue: SUM(net_revenue_gbp) for the calendar month containing as_of."""
    ctx, as_of = _resolve(ctx, as_of)
    rev = ctx.get("fact_revenue")
    start, end = month_bounds(as_of)
    cur = _month_revenue(rev, start, end)
    cur_total = float(cur["net_revenue_gbp"].sum()) if len(cur) else 0.0

    p_start, p_end = previous_month_bounds(as_of)
    prev = _month_revenue(rev, p_start, p_end)
    prev_total = float(prev["net_revenue_gbp"].sum()) if len(prev) else 0.0

    return KPIResult(
        name="total_revenue", value=round(cur_total, 2), unit="gbp",
        as_of=as_of, period_label=start.strftime("%Y-%m"),
        previous_value=round(prev_total, 2),
        breakdown={
            "by_revenue_type": cur.groupby("revenue_type")["net_revenue_gbp"]
                                  .sum().round(2).to_dict() if len(cur) else {},
        },
    )


def revenue_growth(ctx: Optional[DataContext] = None,
                   as_of: Optional[date] = None) -> KPIResult:
    """MoM Revenue Growth %: (Revenue_M - Revenue_M-1) / Revenue_M-1 x 100."""
    ctx, as_of = _resolve(ctx, as_of)
    total = total_revenue(ctx, as_of)
    growth_pct = safe_pct_change(total.value, total.previous_value or 0.0)
    return KPIResult(
        name="revenue_growth", value=growth_pct, unit="percent",
        as_of=as_of, period_label=total.period_label,
        metadata={"current_revenue_gbp": total.value, "previous_revenue_gbp": total.previous_value},
    )


# ── Dimensional breakdowns ───────────────────────────────────────────────────────

def revenue_by_product(ctx: Optional[DataContext] = None,
                       as_of: Optional[date] = None) -> KPIResult:
    """Revenue by Product: SUM(net_revenue_gbp) grouped by product_code for the month."""
    ctx, as_of = _resolve(ctx, as_of)
    rev = ctx.get("fact_revenue")
    start, end = month_bounds(as_of)
    cur = _month_revenue(rev, start, end)

    if not len(cur):
        return KPIResult(name="revenue_by_product", value=0.0, unit="gbp", as_of=as_of)

    by_product = cur.groupby("product_code")["net_revenue_gbp"].sum().round(2)
    total = float(by_product.sum())

    return KPIResult(
        name="revenue_by_product", value=round(total, 2), unit="gbp",
        as_of=as_of, period_label=start.strftime("%Y-%m"),
        breakdown={"by_product": by_product.to_dict()},
    )


def revenue_by_country(ctx: Optional[DataContext] = None,
                       as_of: Optional[date] = None) -> KPIResult:
    """Revenue by Country: SUM(net_revenue_gbp) grouped by country_code for the month."""
    ctx, as_of = _resolve(ctx, as_of)
    rev = ctx.get("fact_revenue")
    start, end = month_bounds(as_of)
    cur = _month_revenue(rev, start, end)

    if not len(cur):
        return KPIResult(name="revenue_by_country", value=0.0, unit="gbp", as_of=as_of)

    by_country = cur.groupby("country_code")["net_revenue_gbp"].sum().round(2)
    total = float(by_country.sum())

    return KPIResult(
        name="revenue_by_country", value=round(total, 2), unit="gbp",
        as_of=as_of, period_label=start.strftime("%Y-%m"),
        breakdown={"by_country": by_country.to_dict()},
    )


def revenue_by_segment(ctx: Optional[DataContext] = None,
                       as_of: Optional[date] = None) -> KPIResult:
    """
    Revenue by Customer Segment: SUM(net_revenue_gbp) grouped by the
    customer's customer_segment, joined from dim_customer.
    """
    ctx, as_of = _resolve(ctx, as_of)
    rev = ctx.get("fact_revenue")
    cust = ctx.get("dim_customer")
    start, end = month_bounds(as_of)
    cur = _month_revenue(rev, start, end)

    if not len(cur) or not len(cust):
        return KPIResult(name="revenue_by_segment", value=0.0, unit="gbp", as_of=as_of)

    merged = cur.merge(
        cust[["customer_id", "customer_segment"]], on="customer_id", how="left"
    )
    by_segment = merged.groupby("customer_segment")["net_revenue_gbp"].sum().round(2)
    total = float(by_segment.sum())

    return KPIResult(
        name="revenue_by_segment", value=round(total, 2), unit="gbp",
        as_of=as_of, period_label=start.strftime("%Y-%m"),
        breakdown={"by_segment": by_segment.to_dict()},
    )


# ── Per-customer economics ───────────────────────────────────────────────────────

def arpu(ctx: Optional[DataContext] = None,
        as_of: Optional[date] = None) -> KPIResult:
    """
    Monthly ARPU = total net revenue in month / MAU in that month.
    kpi_definitions.md Module 2.
    """
    from analytics.kpis.customer_kpis import monthly_active_users

    ctx, as_of = _resolve(ctx, as_of)
    rev_kpi = total_revenue(ctx, as_of)
    mau_kpi = monthly_active_users(ctx, as_of)

    value = round(safe_ratio(rev_kpi.value, mau_kpi.value), 2)

    p_rev = rev_kpi.previous_value or 0.0
    prev_mau_result = monthly_active_users(
        ctx, previous_month_bounds(as_of)[1]
    )
    prev_value = round(safe_ratio(p_rev, prev_mau_result.value), 2)

    return KPIResult(
        name="arpu", value=value, unit="gbp",
        as_of=as_of, period_label=rev_kpi.period_label,
        previous_value=prev_value,
        metadata={"total_revenue_gbp": rev_kpi.value, "mau": mau_kpi.value},
    )


def clv(ctx: Optional[DataContext] = None,
       as_of: Optional[date] = None) -> KPIResult:
    """
    Customer Lifetime Value = ARPU x Average Lifespan (months) x Gross Margin.
    Average lifespan is estimated from observed customer tenure
    (signup_date to churn_date or as_of for active customers) — a
    simple, explainable survival proxy rather than a full survival model.
    """
    ctx, as_of = _resolve(ctx, as_of)
    cust = ctx.get("dim_customer")
    arpu_kpi = arpu(ctx, as_of)

    if not len(cust):
        return KPIResult(name="clv", value=0.0, unit="gbp", as_of=as_of)

    activated = cust[cust["activation_date"].notna()].copy()
    if not len(activated):
        return KPIResult(name="clv", value=0.0, unit="gbp", as_of=as_of)

    as_of_ts = pd.Timestamp(as_of)
    end_date = activated["churn_date"].fillna(as_of_ts)
    end_date = end_date.where(end_date <= as_of_ts, as_of_ts)
    lifespan_days = (end_date - activated["activation_date"]).dt.days.clip(lower=1)
    avg_lifespan_months = float((lifespan_days / 30.44).mean())

    value = round(arpu_kpi.value * avg_lifespan_months * GROSS_MARGIN_ASSUMPTION, 2)

    return KPIResult(
        name="clv", value=value, unit="gbp",
        as_of=as_of, period_label=as_of.isoformat(),
        metadata={
            "arpu_gbp": arpu_kpi.value,
            "avg_lifespan_months": round(avg_lifespan_months, 1),
            "gross_margin_assumption": GROSS_MARGIN_ASSUMPTION,
        },
    )


def ltv_cac_ratio(ctx: Optional[DataContext] = None,
                  as_of: Optional[date] = None) -> KPIResult:
    """
    LTV/CAC Ratio: CLV divided by blended CAC for the month.
    Industry benchmark: > 3.0 is healthy, < 1.0 is loss-making acquisition.
    """
    ctx, as_of = _resolve(ctx, as_of)
    clv_kpi = clv(ctx, as_of)
    mkt = ctx.get("fact_marketing")
    start, end = month_bounds(as_of)

    if not len(mkt):
        return KPIResult(name="ltv_cac_ratio", value=0.0, unit="ratio", as_of=as_of)

    period_mkt = mkt[mkt["touchpoint_date"].dt.date.between(start, end)]
    converted = period_mkt[period_mkt["is_converted"] == True]
    cac = safe_ratio(
        float(period_mkt["acquisition_cost_gbp"].sum()), len(converted)
    ) if len(converted) else 0.0

    ratio = round(safe_ratio(clv_kpi.value, cac), 2) if cac > 0 else 0.0

    return KPIResult(
        name="ltv_cac_ratio", value=ratio, unit="ratio",
        as_of=as_of, period_label=start.strftime("%Y-%m"),
        metadata={
            "clv_gbp": clv_kpi.value, "blended_cac_gbp": round(cac, 2),
            "converted_customers": len(converted),
            "benchmark": "healthy >3.0, concerning <1.0",
        },
    )
