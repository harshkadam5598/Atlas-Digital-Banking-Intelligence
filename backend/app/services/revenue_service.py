"""
Atlas – Revenue Service

Orchestration layer for Revenue Intelligence Hub. Every number traces
to revenue_kpis.py / forecast_engine.py. Contract gap: revenue KPIs are
calendar-month-scoped, not arbitrary date-range; day/week trend has no
backing capability (only monthly series exists).
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from analytics.forecasting.forecast_engine import forecast_revenue
from analytics.kpis.registry import compute

_NO_RANGE_AGGREGATION_NOTE = (
    "Sprint 5 revenue KPIs are calendar-month-scoped around a single "
    "as_of date; there is no analytics-engine function that aggregates "
    "an arbitrary start_date/end_date range. as_of was resolved from "
    "end_date (or today) and this response reflects that calendar month."
)
_NO_SUBMONTHLY_TREND_NOTE = (
    "No backing KPI/forecast capability produces a day- or week-level "
    "revenue time series in the Sprint 5 analytics engine — only a "
    "monthly series exists. Returning an empty series rather than "
    "fabricating one."
)


def get_revenue_summary(start_date: Optional[date], end_date: Optional[date]) -> dict:
    as_of = end_date or start_date
    result = compute("total_revenue", as_of=as_of)
    data = result.to_dict()
    data["requested_range"] = {
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
    }
    data["range_note"] = _NO_RANGE_AGGREGATION_NOTE
    return data


def get_revenue_trend(granularity: str) -> dict:
    if granularity != "month":
        return {"granularity": granularity, "series": [],
                "unavailable_fields": {"series": _NO_SUBMONTHLY_TREND_NOTE}}
    forecast = forecast_revenue(horizon_months=1)
    return {"granularity": "month", "series": forecast.historical}


def get_revenue_forecast() -> dict:
    forecast = forecast_revenue(horizon_months=3)
    data = forecast.to_dict()
    data["horizon_note"] = (
        "Sprint 5 forecast_revenue() operates in monthly horizons. "
        "horizon_months=3 is used as the closest equivalent to a "
        "'90-day forecast' requested by the contract."
    )
    return data
