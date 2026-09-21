"""
Atlas – Market Service

Orchestration layer for the Market Intelligence API. Every underlying
number traces to a real function in analytics/kpis/revenue_kpis.py,
analytics/kpis/customer_kpis.py, or analytics/anomaly/anomaly_engine.py.

docs/business/kpi_definitions.md Module 7 (Market Intelligence) defines
exactly two formulas:
  - Geographic Revenue Contribution = SUM(revenue) BY country /
    SUM(total_revenue) x 100
  - Country Customer Growth Rate MoM = (new_customers_M -
    new_customers_M-1) / new_customers_M-1 x 100, per country

Neither has a dedicated KPI function — both are derived here as plain
arithmetic on the outputs of two already-real, already-registered
functions (revenue_by_country, new_customers). No new KPI was added to
analytics/kpis/ and the registry was not modified for Market.

"Market efficiency" (the fourth requested endpoint) is NOT a term
defined anywhere in kpi_definitions.md, the master spec, or the API
contracts. There is no formally defined Market Efficiency KPI in
Atlas. /market/efficiency exposes ltv_cac_ratio — a genuine
acquisition-efficiency metric already used elsewhere (Customer's
/value endpoint) — explicitly labeled as the closest available proxy,
not as a claim that this is "the" Market Efficiency metric.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from analytics.anomaly.anomaly_engine import detect_country_anomalies
from analytics.kpis import customer_kpis
from analytics.kpis.periods import previous_month_bounds
from analytics.kpis.registry import compute

_EFFICIENCY_PROXY_NOTE = (
    "Atlas has no formally defined 'Market Efficiency' KPI — this term "
    "does not appear in docs/business/kpi_definitions.md or the master "
    "spec. ltv_cac_ratio (LTV/CAC) is exposed here as the closest "
    "available acquisition-efficiency proxy, not as a claim that this "
    "is an officially defined Market Efficiency metric."
)


def get_summary(as_of: Optional[date] = None) -> dict:
    revenue = compute("revenue_by_country", as_of=as_of)
    efficiency = compute("ltv_cac_ratio", as_of=as_of)

    return {
        "total_revenue": revenue.value,
        "top_countries_by_revenue": revenue.breakdown.get("by_country", {}) if revenue.breakdown else {},
        "ltv_cac_ratio": efficiency.value,
        "as_of_date": revenue.as_of.isoformat(),
        "efficiency_note": _EFFICIENCY_PROXY_NOTE,
    }


def get_geographic(as_of: Optional[date] = None) -> dict:
    """
    Real revenue_by_country() output, plus two derived figures per the
    documented Module 7 formulas — computed as plain arithmetic on
    already-fetched real function outputs, not new KPI logic:
      - Geographic Revenue Contribution %: each country's share of
        by_country / the KPI's own total value.
      - Country Customer Growth Rate MoM: diff between two
        new_customers() calls' by_country breakdowns (this month vs
        previous month), iterating the union of both periods' countries
        so a country dropping to zero this month is reported as a
        defined -100.0% decline rather than silently omitted.
    """
    revenue = compute("revenue_by_country", as_of=as_of)
    by_country_revenue = revenue.breakdown.get("by_country", {}) if revenue.breakdown else {}
    total_revenue = revenue.value

    contribution_pct = {
        country: round((amount / total_revenue) * 100, 2) if total_revenue else 0.0
        for country, amount in by_country_revenue.items()
    }

    current = customer_kpis.new_customers(as_of=as_of)
    prev_start, _ = previous_month_bounds(current.as_of)
    previous = customer_kpis.new_customers(as_of=prev_start)

    current_by_country = current.breakdown.get("by_country", {}) if current.breakdown else {}
    previous_by_country = previous.breakdown.get("by_country", {}) if previous.breakdown else {}

    all_countries = set(current_by_country) | set(previous_by_country)
    growth_rate_mom = {}
    for country in all_countries:
        curr_count = current_by_country.get(country, 0)
        prev_count = previous_by_country.get(country, 0)
        if prev_count:
            growth_rate_mom[country] = round(
                (curr_count - prev_count) / prev_count * 100, 2
            )
        else:
            growth_rate_mom[country] = None  # undefined MoM rate with a zero prior-month base

    return {
        "revenue_by_country": by_country_revenue,
        "total_revenue": total_revenue,
        "geographic_revenue_contribution_pct": contribution_pct,
        "country_customer_growth_rate_mom": growth_rate_mom,
        "new_customers_current_month": current_by_country,
        "new_customers_previous_month": previous_by_country,
        "as_of_date": revenue.as_of.isoformat(),
        "note": (
            "geographic_revenue_contribution_pct and "
            "country_customer_growth_rate_mom are derived at the API "
            "orchestration layer from revenue_by_country() and two "
            "new_customers() calls, per kpi_definitions.md Module 7 — "
            "neither is a new KPI function."
        ),
    }


def get_anomalies() -> dict:
    anomalies = detect_country_anomalies()
    return {
        "count": len(anomalies),
        "anomalies": [a.to_dict() for a in anomalies],
    }


def get_efficiency(as_of: Optional[date] = None) -> dict:
    result = compute("ltv_cac_ratio", as_of=as_of)
    data = result.to_dict()
    data["proxy_note"] = _EFFICIENCY_PROXY_NOTE
    return data
