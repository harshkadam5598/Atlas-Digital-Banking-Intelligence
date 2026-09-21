"""
Atlas KPI Engine — Operations Domain

KYC Approval Rate, Average Processing Time, Support Resolution Time,
CSAT, Fraud Rate, Failed Transaction Rate. Formulas trace to
docs/business/kpi_definitions.md Module 6 (Operational Intelligence).
"""

from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd

from analytics.core.data_context import DataContext, get_data_context
from analytics.core.types import KPIResult
from analytics.kpis.periods import month_bounds, safe_ratio

FRAUD_EVENT_TYPES = {"fraud_flagged", "fraud_cleared", "suspicious_transfer", "chargeback"}


def _resolve(ctx: Optional[DataContext], as_of: Optional[date]):
    ctx = ctx or get_data_context()
    as_of = as_of or ctx.as_of()
    return ctx, as_of


def kyc_approval_rate(ctx: Optional[DataContext] = None,
                      as_of: Optional[date] = None) -> KPIResult:
    """KYC Approval Rate: COUNT(outcome='approved') / COUNT(submissions) x 100. Target >=85%."""
    ctx, as_of = _resolve(ctx, as_of)
    kyc = ctx.get("fact_kyc_events")
    start, end = month_bounds(as_of)

    if not len(kyc):
        return KPIResult(name="kyc_approval_rate", value=0.0, unit="percent", as_of=as_of)

    month_kyc = kyc[kyc["submission_date"].dt.date.between(start, end)]
    if not len(month_kyc):
        return KPIResult(name="kyc_approval_rate", value=0.0, unit="percent", as_of=as_of)

    approved = (month_kyc["outcome"] == "approved").sum()
    rate = round(safe_ratio(approved, len(month_kyc)) * 100, 2)

    by_country = (
        month_kyc.groupby("country_code")["outcome"]
        .apply(lambda s: round(safe_ratio((s == "approved").sum(), len(s)) * 100, 2))
        .to_dict()
    )

    return KPIResult(
        name="kyc_approval_rate", value=rate, unit="percent",
        as_of=as_of, period_label=start.strftime("%Y-%m"),
        metadata={"target": 85.0, "total_submissions": len(month_kyc), "approved": int(approved)},
        breakdown={"by_country": by_country},
    )


def kyc_processing_time(ctx: Optional[DataContext] = None,
                        as_of: Optional[date] = None) -> KPIResult:
    """KYC Median Processing Time in hours. Target < 24 hours."""
    ctx, as_of = _resolve(ctx, as_of)
    kyc = ctx.get("fact_kyc_events")
    start, end = month_bounds(as_of)

    if not len(kyc):
        return KPIResult(name="kyc_processing_time", value=0.0, unit="hours", as_of=as_of)

    month_kyc = kyc[kyc["submission_date"].dt.date.between(start, end)]
    valid = month_kyc["processing_time_hours"].dropna()
    if not len(valid):
        return KPIResult(name="kyc_processing_time", value=0.0, unit="hours", as_of=as_of)

    median_hours = round(float(valid.median()), 2)
    mean_hours = round(float(valid.mean()), 2)

    return KPIResult(
        name="kyc_processing_time", value=median_hours, unit="hours",
        as_of=as_of, period_label=start.strftime("%Y-%m"),
        metadata={"target_hours": 24.0, "mean_hours": mean_hours, "sample_size": len(valid)},
    )


def support_resolution_time(ctx: Optional[DataContext] = None,
                            as_of: Optional[date] = None) -> KPIResult:
    """Average Resolution Time per ticket priority, in hours. P1 target <4h, P2 target <24h."""
    ctx, as_of = _resolve(ctx, as_of)
    sup = ctx.get("fact_support")
    start, end = month_bounds(as_of)

    if not len(sup):
        return KPIResult(name="support_resolution_time", value=0.0, unit="hours", as_of=as_of)

    month_sup = sup[
        sup["created_date"].dt.date.between(start, end) & (sup["status"] == "resolved")
    ]
    if not len(month_sup):
        return KPIResult(name="support_resolution_time", value=0.0, unit="hours", as_of=as_of)

    overall_avg = round(float(month_sup["resolution_time_hours"].mean()), 2)
    by_priority = month_sup.groupby("priority")["resolution_time_hours"].mean().round(2).to_dict()

    return KPIResult(
        name="support_resolution_time", value=overall_avg, unit="hours",
        as_of=as_of, period_label=start.strftime("%Y-%m"),
        metadata={"targets": {"P1": 4.0, "P2": 24.0}, "resolved_tickets": len(month_sup)},
        breakdown={"by_priority": by_priority},
    )


def csat(ctx: Optional[DataContext] = None,
        as_of: Optional[date] = None) -> KPIResult:
    """CSAT: average satisfaction_score (1-5) for resolved tickets with a rating."""
    ctx, as_of = _resolve(ctx, as_of)
    sup = ctx.get("fact_support")
    start, end = month_bounds(as_of)

    if not len(sup):
        return KPIResult(name="csat", value=0.0, unit="score", as_of=as_of)

    month_sup = sup[sup["created_date"].dt.date.between(start, end)]
    rated = month_sup["satisfaction_score"].dropna()
    if not len(rated):
        return KPIResult(name="csat", value=0.0, unit="score", as_of=as_of)

    avg_score = round(float(rated.mean()), 2)
    premium_rated = month_sup[month_sup["is_premium_customer"] == True]["satisfaction_score"].dropna()
    free_rated = month_sup[month_sup["is_premium_customer"] == False]["satisfaction_score"].dropna()

    return KPIResult(
        name="csat", value=avg_score, unit="score",
        as_of=as_of, period_label=start.strftime("%Y-%m"),
        metadata={"scale": "1-5", "rated_tickets": len(rated)},
        breakdown={
            "by_tier": {
                "premium": round(float(premium_rated.mean()), 2) if len(premium_rated) else 0.0,
                "free": round(float(free_rated.mean()), 2) if len(free_rated) else 0.0,
            }
        },
    )


def fraud_rate(ctx: Optional[DataContext] = None,
              as_of: Optional[date] = None) -> KPIResult:
    """Fraud Rate: COUNT(fraud_flagged events) / COUNT(completed transactions) x 100."""
    ctx, as_of = _resolve(ctx, as_of)
    evt = ctx.get("fact_product_events")
    txn = ctx.get("fact_transactions")
    start, end = month_bounds(as_of)

    if not len(evt) or not len(txn):
        return KPIResult(name="fraud_rate", value=0.0, unit="percent", as_of=as_of)

    month_evt = evt[evt["event_date"].dt.date.between(start, end)]
    month_txn = txn[
        txn["transaction_date"].dt.date.between(start, end) & (txn["status"] == "completed")
    ]

    flagged = (month_evt["event_type"] == "fraud_flagged").sum()
    cleared = (month_evt["event_type"] == "fraud_cleared").sum()
    chargebacks = (month_evt["event_type"] == "chargeback").sum()

    rate = round(safe_ratio(flagged, len(month_txn)) * 100, 4)
    clear_ratio = round(safe_ratio(cleared, flagged) * 100, 2) if flagged else 0.0

    return KPIResult(
        name="fraud_rate", value=rate, unit="percent",
        as_of=as_of, period_label=start.strftime("%Y-%m"),
        metadata={
            "flagged_count": int(flagged), "cleared_count": int(cleared),
            "chargeback_count": int(chargebacks), "clear_ratio_pct": clear_ratio,
            "completed_transactions": len(month_txn),
        },
    )


def failed_transaction_rate(ctx: Optional[DataContext] = None,
                            as_of: Optional[date] = None) -> KPIResult:
    """Failed Transaction Rate: COUNT(status='failed') / COUNT(ALL) x 100. Alert threshold >2%."""
    ctx, as_of = _resolve(ctx, as_of)
    txn = ctx.get("fact_transactions")
    start, end = month_bounds(as_of)

    if not len(txn):
        return KPIResult(name="failed_transaction_rate", value=0.0, unit="percent", as_of=as_of)

    month_txn = txn[txn["transaction_date"].dt.date.between(start, end)]
    if not len(month_txn):
        return KPIResult(name="failed_transaction_rate", value=0.0, unit="percent", as_of=as_of)

    failed = (month_txn["status"] == "failed").sum()
    rate = round(safe_ratio(failed, len(month_txn)) * 100, 2)

    by_product = (
        month_txn.groupby("product_code")["status"]
        .apply(lambda s: round(safe_ratio((s == "failed").sum(), len(s)) * 100, 2))
        .to_dict()
    )

    return KPIResult(
        name="failed_transaction_rate", value=rate, unit="percent",
        as_of=as_of, period_label=start.strftime("%Y-%m"),
        metadata={"alert_threshold": 2.0, "failed_count": int(failed), "total_transactions": len(month_txn)},
        breakdown={"by_product": by_product},
    )
