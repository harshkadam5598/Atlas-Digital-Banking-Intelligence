"""
Atlas KPI Engine — Customer Domain

Implements every customer KPI listed in the Sprint 5 spec:
  DAU, WAU, MAU, Active Customers, New Customers, Returning Customers,
  Churn Rate, Retention Rate, Premium Conversion Rate.

All functions share the same signature pattern:
    kpi_fn(ctx: DataContext, as_of: Optional[date] = None) -> KPIResult

Every function is independently callable and independently testable —
no function depends on another function's return value, only on the
DataContext. Formulas trace directly to docs/business/kpi_definitions.md.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import pandas as pd
from loguru import logger

from analytics.core.data_context import DataContext, get_data_context
from analytics.core.types import KPIResult
from analytics.kpis.periods import (
    month_bounds, previous_month_bounds, rolling_window, safe_pct_change, safe_ratio,
)

ACTIVE_LIFECYCLE_STAGES = {"activated", "reactivated"}


def _resolve(ctx: Optional[DataContext], as_of: Optional[date]):
    ctx = ctx or get_data_context()
    as_of = as_of or ctx.as_of()
    return ctx, as_of


def _activity_dates(ctx: DataContext) -> pd.DataFrame:
    """
    Build a unified (customer_id, activity_date) table from transactions
    and product events — the two sources of "the customer did something".
    Used by DAU/WAU/MAU and churn/retention.
    """
    txn = ctx.get("fact_transactions")
    evt = ctx.get("fact_product_events")

    frames = []
    if len(txn):
        frames.append(txn[["customer_id", "transaction_date"]].rename(
            columns={"transaction_date": "activity_date"}))
    if len(evt):
        frames.append(evt[["customer_id", "event_date"]].rename(
            columns={"event_date": "activity_date"}))

    if not frames:
        return pd.DataFrame({
            "customer_id": pd.Series(dtype="object"),
            "activity_date": pd.Series(dtype="datetime64[ns]"),
        })

    combined = pd.concat(frames, ignore_index=True)
    combined["activity_date"] = pd.to_datetime(combined["activity_date"])
    return combined


# ── Active user counts ──────────────────────────────────────────────────────────

def daily_active_users(ctx: Optional[DataContext] = None,
                       as_of: Optional[date] = None) -> KPIResult:
    """DAU: distinct customers with any transaction or product event on as_of."""
    ctx, as_of = _resolve(ctx, as_of)
    activity = _activity_dates(ctx)
    today_mask = activity["activity_date"].dt.date == as_of
    dau = activity.loc[today_mask, "customer_id"].nunique()

    prev_day = as_of - timedelta(days=1)
    prev_mask = activity["activity_date"].dt.date == prev_day
    prev_dau = activity.loc[prev_mask, "customer_id"].nunique()

    return KPIResult(
        name="daily_active_users", value=float(dau), unit="count",
        as_of=as_of, period_label=as_of.isoformat(),
        previous_value=float(prev_dau),
    )


def weekly_active_users(ctx: Optional[DataContext] = None,
                        as_of: Optional[date] = None) -> KPIResult:
    """WAU: distinct customers active in the trailing 7-day window ending as_of."""
    ctx, as_of = _resolve(ctx, as_of)
    activity = _activity_dates(ctx)
    start, end = rolling_window(as_of, 7)
    mask = activity["activity_date"].dt.date.between(start, end)
    wau = activity.loc[mask, "customer_id"].nunique()

    prev_start, prev_end = rolling_window(start - timedelta(days=1), 7)
    prev_mask = activity["activity_date"].dt.date.between(prev_start, prev_end)
    prev_wau = activity.loc[prev_mask, "customer_id"].nunique()

    return KPIResult(
        name="weekly_active_users", value=float(wau), unit="count",
        as_of=as_of, period_label=f"{start.isoformat()}_to_{end.isoformat()}",
        previous_value=float(prev_wau),
    )


def monthly_active_users(ctx: Optional[DataContext] = None,
                         as_of: Optional[date] = None) -> KPIResult:
    """
    MAU: distinct customers with >=1 transaction or product event in the
    calendar month containing as_of. Excludes KYC-pending and churned
    customers per kpi_definitions.md Module 1.
    """
    ctx, as_of = _resolve(ctx, as_of)
    activity = _activity_dates(ctx)
    start, end = month_bounds(as_of)
    mask = activity["activity_date"].dt.date.between(start, end)
    mau = activity.loc[mask, "customer_id"].nunique()

    p_start, p_end = previous_month_bounds(as_of)
    p_mask = activity["activity_date"].dt.date.between(p_start, p_end)
    prev_mau = activity.loc[p_mask, "customer_id"].nunique()

    cust = ctx.get("dim_customer")
    by_country = {}
    by_segment = {}
    if len(cust) and len(activity):
        active_ids = set(activity.loc[mask, "customer_id"])
        active_cust = cust[cust["customer_id"].isin(active_ids)]
        if "country_code" in active_cust.columns:
            by_country = active_cust["country_code"].value_counts().to_dict()
        if "customer_segment" in active_cust.columns:
            by_segment = active_cust["customer_segment"].value_counts().to_dict()

    return KPIResult(
        name="monthly_active_users", value=float(mau), unit="count",
        as_of=as_of, period_label=start.strftime("%Y-%m"),
        previous_value=float(prev_mau),
        breakdown={"by_country": by_country, "by_segment": by_segment},
    )


def active_customers(ctx: Optional[DataContext] = None,
                     as_of: Optional[date] = None) -> KPIResult:
    """
    Active Customers: count of dim_customer rows whose lifecycle_stage is
    'activated' or 'reactivated' as of as_of (point-in-time snapshot,
    not a rolling activity window like MAU).
    """
    ctx, as_of = _resolve(ctx, as_of)
    cust = ctx.get("dim_customer")
    if not len(cust):
        return KPIResult(name="active_customers", value=0.0, unit="count", as_of=as_of)

    active = cust[cust["lifecycle_stage"].isin(ACTIVE_LIFECYCLE_STAGES)]
    return KPIResult(
        name="active_customers", value=float(len(active)), unit="count",
        as_of=as_of, period_label=as_of.isoformat(),
        breakdown={
            "by_segment": active["customer_segment"].value_counts().to_dict()
                          if "customer_segment" in active.columns else {},
        },
    )


# ── Acquisition ──────────────────────────────────────────────────────────────────

def new_customers(ctx: Optional[DataContext] = None,
                  as_of: Optional[date] = None) -> KPIResult:
    """New Customers: count of dim_customer rows with signup_date in as_of's month."""
    ctx, as_of = _resolve(ctx, as_of)
    cust = ctx.get("dim_customer")
    start, end = month_bounds(as_of)
    if not len(cust):
        return KPIResult(name="new_customers", value=0.0, unit="count", as_of=as_of)

    mask = cust["signup_date"].dt.date.between(start, end)
    count = int(mask.sum())

    p_start, p_end = previous_month_bounds(as_of)
    prev_mask = cust["signup_date"].dt.date.between(p_start, p_end)
    prev_count = int(prev_mask.sum())

    return KPIResult(
        name="new_customers", value=float(count), unit="count",
        as_of=as_of, period_label=start.strftime("%Y-%m"),
        previous_value=float(prev_count),
        breakdown={
            "by_channel": cust.loc[mask, "channel_code"].value_counts().to_dict()
                          if "channel_code" in cust.columns else {},
            "by_country": cust.loc[mask, "country_code"].value_counts().to_dict()
                          if "country_code" in cust.columns else {},
        },
    )


def returning_customers(ctx: Optional[DataContext] = None,
                        as_of: Optional[date] = None) -> KPIResult:
    """
    Returning Customers: customers active in as_of's month who were ALSO
    active in the previous month (i.e. not new, and not a one-off reactivation
    that lapses again — simple month-over-month presence).
    """
    ctx, as_of = _resolve(ctx, as_of)
    activity = _activity_dates(ctx)
    if not len(activity):
        return KPIResult(name="returning_customers", value=0.0, unit="count", as_of=as_of)

    cur_start, cur_end = month_bounds(as_of)
    prev_start, prev_end = previous_month_bounds(as_of)

    cur_ids = set(activity.loc[
        activity["activity_date"].dt.date.between(cur_start, cur_end), "customer_id"
    ])
    prev_ids = set(activity.loc[
        activity["activity_date"].dt.date.between(prev_start, prev_end), "customer_id"
    ])

    returning = cur_ids & prev_ids
    return KPIResult(
        name="returning_customers", value=float(len(returning)), unit="count",
        as_of=as_of, period_label=cur_start.strftime("%Y-%m"),
        metadata={"current_month_active": len(cur_ids), "previous_month_active": len(prev_ids)},
    )


# ── Churn & retention ────────────────────────────────────────────────────────────

def churn_rate(ctx: Optional[DataContext] = None,
              as_of: Optional[date] = None) -> KPIResult:
    """
    Monthly Churn Rate per kpi_definitions.md Module 2:
    % of customers active in month M-1 who had zero activity in month M.
    """
    ctx, as_of = _resolve(ctx, as_of)
    activity = _activity_dates(ctx)
    if not len(activity):
        return KPIResult(name="churn_rate", value=0.0, unit="percent", as_of=as_of)

    cur_start, cur_end = month_bounds(as_of)
    prev_start, prev_end = previous_month_bounds(as_of)

    prev_ids = set(activity.loc[
        activity["activity_date"].dt.date.between(prev_start, prev_end), "customer_id"
    ])
    cur_ids = set(activity.loc[
        activity["activity_date"].dt.date.between(cur_start, cur_end), "customer_id"
    ])

    churned = prev_ids - cur_ids
    rate = safe_ratio(len(churned), len(prev_ids)) * 100

    return KPIResult(
        name="churn_rate", value=round(rate, 2), unit="percent",
        as_of=as_of, period_label=cur_start.strftime("%Y-%m"),
        metadata={"churned_count": len(churned), "prior_active_base": len(prev_ids)},
    )


def retention_rate(ctx: Optional[DataContext] = None,
                   as_of: Optional[date] = None,
                   period_months: int = 1) -> KPIResult:
    """
    Cohort Retention Rate: % of customers from the signup cohort
    `period_months` months ago who are still active as_of.
    Mirrors analytics.v_cohort_retention from the SQL layer.
    """
    ctx, as_of = _resolve(ctx, as_of)
    cust = ctx.get("dim_customer")
    activity = _activity_dates(ctx)
    if not len(cust):
        return KPIResult(name="retention_rate", value=0.0, unit="percent", as_of=as_of)

    cohort_month_start, cohort_month_end = month_bounds(
        as_of.replace(day=1) - timedelta(days=1)
    )
    for _ in range(period_months - 1):
        cohort_month_start, cohort_month_end = previous_month_bounds(cohort_month_start)

    cohort = cust[cust["signup_date"].dt.date.between(cohort_month_start, cohort_month_end)]
    cohort_size = len(cohort)
    if cohort_size == 0:
        return KPIResult(
            name="retention_rate", value=0.0, unit="percent", as_of=as_of,
            metadata={"cohort_size": 0, "period_months": period_months},
        )

    window_start, window_end = rolling_window(as_of, 30)
    active_recent = set(activity.loc[
        activity["activity_date"].dt.date.between(window_start, window_end), "customer_id"
    ])
    retained = cohort[cohort["customer_id"].isin(active_recent)]
    rate = safe_ratio(len(retained), cohort_size) * 100

    return KPIResult(
        name="retention_rate", value=round(rate, 2), unit="percent",
        as_of=as_of, period_label=f"M+{period_months}",
        metadata={
            "cohort_size": cohort_size, "retained_count": len(retained),
            "cohort_month": cohort_month_start.strftime("%Y-%m"),
            "period_months": period_months,
        },
    )


def premium_conversion_rate(ctx: Optional[DataContext] = None,
                            as_of: Optional[date] = None) -> KPIResult:
    """Premium Conversion Rate: % of activated customers with premium_status=True."""
    ctx, as_of = _resolve(ctx, as_of)
    cust = ctx.get("dim_customer")
    if not len(cust):
        return KPIResult(name="premium_conversion_rate", value=0.0, unit="percent", as_of=as_of)

    activated = cust[cust["lifecycle_stage"].isin(
        ACTIVE_LIFECYCLE_STAGES | {"churned"})]
    if len(activated) == 0:
        return KPIResult(name="premium_conversion_rate", value=0.0, unit="percent", as_of=as_of)

    rate = safe_ratio(int(activated["premium_status"].sum()), len(activated)) * 100

    by_country = (
        activated.groupby("country_code")["premium_status"].mean().mul(100).round(2).to_dict()
        if "country_code" in activated.columns else {}
    )

    return KPIResult(
        name="premium_conversion_rate", value=round(rate, 2), unit="percent",
        as_of=as_of, period_label=as_of.isoformat(),
        metadata={
            "premium_count": int(activated["premium_status"].sum()),
            "activated_base": len(activated),
        },
        breakdown={"by_country": by_country},
    )
