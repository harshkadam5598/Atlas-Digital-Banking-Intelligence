"""
Atlas – Growth Service. Orchestrates growth_kpis.py. activation-trend
built by calling activation_rate() once per month (same pattern as
/revenue/trend), since it's month-scoped like every other point-in-time
KPI in the engine.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from analytics.kpis import growth_kpis
from analytics.kpis.periods import month_bounds
from analytics.kpis.registry import compute


def get_funnel(as_of: Optional[date] = None) -> dict:
    return compute("funnel_conversion", as_of=as_of).to_dict()


def get_cac_by_channel(as_of: Optional[date] = None) -> dict:
    return compute("cac_by_channel", as_of=as_of).to_dict()


def get_activation_trend(months: int, as_of: Optional[date] = None) -> dict:
    anchor = as_of or growth_kpis.get_data_context().as_of()
    series = []
    cursor = anchor
    for _ in range(months):
        result = growth_kpis.activation_rate(ctx=None, as_of=cursor)
        series.append({
            "period": result.period_label,
            "activation_rate": result.value,
            "registrations": (result.metadata or {}).get("registrations", 0),
        })
        first_of_month, _ = month_bounds(cursor)
        cursor = first_of_month - timedelta(days=1)
    series.reverse()
    return {"granularity": "month", "series": series}
