"""
Atlas KPI Engine — Growth Domain (Sprint 6 approved narrow extension)

Implements exactly the three approved Growth capabilities: funnel
conversion, CAC by channel, activation rate. See
docs/business/kpi_definitions.md Module 3 and sql/schema/{01,02}*.sql
for source data. Visitor->Registration funnel stage omitted (no
visitor/traffic table exists). fact_marketing.is_converted used as
populated by ETL ("reached activation"), not re-derived.
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


def _registration_cohort(cust: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    if not len(cust) or "signup_date" not in cust.columns:
        return cust.iloc[0:0]
    mask = cust["signup_date"].dt.date.between(start, end)
    return cust.loc[mask]


def funnel_conversion(ctx: Optional[DataContext] = None,
                      as_of: Optional[date] = None) -> KPIResult:
    ctx, as_of = _resolve(ctx, as_of)
    cust = ctx.get("dim_customer")
    start, end = month_bounds(as_of)

    if not len(cust):
        return KPIResult(
            name="funnel_conversion", value=0.0, unit="percent", as_of=as_of,
            period_label=start.strftime("%Y-%m"),
            metadata={"note": "No dim_customer data available for this period."},
        )

    cohort = _registration_cohort(cust, start, end)
    registrations = len(cohort)

    if registrations == 0:
        return KPIResult(
            name="funnel_conversion", value=0.0, unit="percent", as_of=as_of,
            period_label=start.strftime("%Y-%m"),
            metadata={"registrations": 0, "note": "No registrations in this period."},
        )

    kyc_started = int(cohort["kyc_submission_date"].notna().sum())
    kyc_approved = int((cohort["kyc_status"] == "approved").sum())
    activated = int(cohort["activation_date"].notna().sum())
    first_txn = int(cohort["first_transaction_date"].notna().sum())
    premium_upgrades = int(
        cohort.loc[cohort["activation_date"].notna(), "premium_status"].sum()
    )

    stage_counts = {
        "registrations": registrations,
        "kyc_started": kyc_started,
        "kyc_approved": kyc_approved,
        "activated": activated,
        "first_transaction": first_txn,
        "premium_upgrades": premium_upgrades,
    }
    stage_conversion_rates = {
        "registration_to_kyc_started": round(safe_ratio(kyc_started, registrations) * 100, 2),
        "kyc_started_to_approved": round(safe_ratio(kyc_approved, kyc_started) * 100, 2),
        "kyc_approved_to_activated": round(safe_ratio(activated, kyc_approved) * 100, 2),
        "activated_to_first_transaction": round(safe_ratio(first_txn, activated) * 100, 2),
        "free_to_premium": round(safe_ratio(premium_upgrades, activated) * 100, 2),
    }

    return KPIResult(
        name="funnel_conversion",
        value=round(safe_ratio(first_txn, registrations) * 100, 2),
        unit="percent", as_of=as_of, period_label=start.strftime("%Y-%m"),
        breakdown={
            "stage_counts": stage_counts,
            "stage_conversion_rates": stage_conversion_rates,
        },
        metadata={
            "note": (
                "Visitor -> Registration stage omitted: no visitor/traffic "
                "data source exists in the Sprint 5 warehouse."
            ),
        },
    )


def cac_by_channel(ctx: Optional[DataContext] = None,
                   as_of: Optional[date] = None) -> KPIResult:
    ctx, as_of = _resolve(ctx, as_of)
    mkt = ctx.get("fact_marketing")
    start, end = month_bounds(as_of)

    if not len(mkt):
        return KPIResult(
            name="cac_by_channel", value=0.0, unit="gbp", as_of=as_of,
            period_label=start.strftime("%Y-%m"),
            metadata={"note": "No fact_marketing data available for this period."},
        )

    period = mkt[mkt["touchpoint_date"].dt.date.between(start, end)]
    if not len(period):
        return KPIResult(
            name="cac_by_channel", value=0.0, unit="gbp", as_of=as_of,
            period_label=start.strftime("%Y-%m"),
            metadata={"note": "No marketing touchpoints in this period."},
        )

    spend_by_channel = period.groupby("channel_code")["acquisition_cost_gbp"].sum().round(2)
    converted_by_channel = (
        period[period["is_converted"] == True]
        .groupby("channel_code")["customer_id"].nunique()
    )

    cac_by_ch = {}
    for channel in spend_by_channel.index:
        spend = float(spend_by_channel.get(channel, 0.0))
        converted = int(converted_by_channel.get(channel, 0))
        cac_by_ch[channel] = round(safe_ratio(spend, converted), 2)

    total_spend = float(spend_by_channel.sum())
    total_converted = int(converted_by_channel.sum()) if len(converted_by_channel) else 0

    zero_converted_channels = [
        ch for ch in spend_by_channel.index if int(converted_by_channel.get(ch, 0)) == 0
    ]

    return KPIResult(
        name="cac_by_channel",
        value=round(safe_ratio(total_spend, total_converted), 2),
        unit="gbp", as_of=as_of, period_label=start.strftime("%Y-%m"),
        breakdown={
            "by_channel": cac_by_ch,
            "spend_by_channel": spend_by_channel.round(2).to_dict(),
            "converted_by_channel": converted_by_channel.to_dict(),
        },
        metadata={
            "converted_definition": (
                "fact_marketing.is_converted as populated by ETL — the "
                "schema documents this as 'reached activation', narrower "
                "than kpi_definitions.md's fuller 'KYC complete AND first "
                "transaction made'. Used as populated, not re-derived."
            ),
            "note": (
                f"Channel(s) with 0 converted customers show CAC as 0.0 "
                f"(safe-division default), meaning 'not computable', not "
                f"'free acquisition': {zero_converted_channels}"
                if zero_converted_channels else None
            ),
        },
    )


def activation_rate(ctx: Optional[DataContext] = None,
                    as_of: Optional[date] = None) -> KPIResult:
    ctx, as_of = _resolve(ctx, as_of)
    cust = ctx.get("dim_customer")
    start, end = month_bounds(as_of)

    if not len(cust):
        return KPIResult(
            name="activation_rate", value=0.0, unit="percent", as_of=as_of,
            period_label=start.strftime("%Y-%m"),
        )

    cohort = _registration_cohort(cust, start, end)
    registrations = len(cohort)
    if registrations == 0:
        return KPIResult(
            name="activation_rate", value=0.0, unit="percent", as_of=as_of,
            period_label=start.strftime("%Y-%m"),
            metadata={"registrations": 0},
        )

    has_txn = cohort["first_transaction_date"].notna()
    days_to_txn = (cohort["first_transaction_date"] - cohort["signup_date"]).dt.days
    within_30d = has_txn & (days_to_txn <= 30)
    activated_within_30d = int(within_30d.sum())

    return KPIResult(
        name="activation_rate",
        value=round(safe_ratio(activated_within_30d, registrations) * 100, 2),
        unit="percent", as_of=as_of, period_label=start.strftime("%Y-%m"),
        metadata={
            "registrations": registrations,
            "activated_within_30d": activated_within_30d,
        },
    )
