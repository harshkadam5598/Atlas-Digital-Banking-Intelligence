"""
Atlas – Executive Service

Orchestration layer for Executive Command Center. Every number traces
to a real analytics function. activation_rate/risk_score/nps_proxy/
operational_uptime are documented in kpi_definitions.md but have no
backing KPI implementation — returned as None with an explanatory note
rather than fabricated.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from analytics.anomaly.anomaly_engine import detect_all_anomalies
from analytics.core.types import Severity
from analytics.kpis import customer_kpis, revenue_kpis
from analytics.kpis.registry import compute

_SEVERITY_ORDER = {Severity.CRITICAL: 0, Severity.HIGH: 1, Severity.MEDIUM: 2, Severity.LOW: 3}
_UNAVAILABLE_KPI_NOTE = (
    "No backing KPI implementation in the Sprint 5 analytics engine. "
    "Documented in docs/business/kpi_definitions.md but not yet built."
)


def get_executive_kpis(as_of: Optional[date] = None) -> dict:
    mau = compute("monthly_active_users", as_of=as_of)
    revenue = compute("total_revenue", as_of=as_of)
    revenue_growth = compute("revenue_growth", as_of=as_of)
    premium_conversion = compute("premium_conversion_rate", as_of=as_of)
    churn = compute("churn_rate", as_of=as_of)

    return {
        "mau": mau.value,
        "mau_growth_mom": round(mau.delta_pct / 100, 4) if mau.delta_pct is not None else None,
        "revenue_mtd": revenue.value,
        "revenue_growth_mom": round(revenue_growth.value / 100, 4),
        "activation_rate": None,
        "premium_conversion_rate": round(premium_conversion.value / 100, 4),
        "churn_rate_monthly": round(churn.value / 100, 4),
        "risk_score": None,
        "as_of_date": mau.as_of.isoformat(),
        "unavailable_fields": {
            "activation_rate": _UNAVAILABLE_KPI_NOTE,
            "risk_score": _UNAVAILABLE_KPI_NOTE,
        },
    }


def get_health_score_components(as_of: Optional[date] = None) -> dict:
    retention = customer_kpis.retention_rate(as_of=as_of, period_months=1)
    revenue_growth = revenue_kpis.revenue_growth(as_of=as_of)

    return {
        "score": None,
        "rating": None,
        "components": {
            "retention_30d": round(retention.value / 100, 4),
            "revenue_growth_mom": round(revenue_growth.value / 100, 4),
            "activation_rate": None,
            "nps_proxy": None,
            "operational_uptime": None,
        },
        "as_of_date": retention.as_of.isoformat(),
        "formula": (
            "(Activation Rate x 0.25) + (30-Day Retention x 0.25) + "
            "(Revenue Growth MoM x 0.20) + (NPS Proxy x 0.15) + "
            "(Operational Uptime x 0.15) — per docs/business/kpi_definitions.md"
        ),
        "unavailable_fields": {
            "activation_rate": _UNAVAILABLE_KPI_NOTE,
            "nps_proxy": _UNAVAILABLE_KPI_NOTE,
            "operational_uptime": "No infrastructure/uptime monitoring exists in Atlas.",
        },
    }


def get_risk_alerts() -> list:
    anomalies = detect_all_anomalies()
    return sorted(anomalies, key=lambda a: _SEVERITY_ORDER.get(a.severity, 99))
