"""
Atlas KPI Engine — Period Utilities

Shared time-window helpers used by every KPI calculation function.
Centralising period logic guarantees every engine uses identical
month/week/day boundary definitions — a frequent source of off-by-one
bugs when each KPI function rolls its own date math.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Tuple


def month_bounds(as_of: date) -> Tuple[date, date]:
    """Return (first_day, last_day) of the calendar month containing as_of."""
    first = as_of.replace(day=1)
    if first.month == 12:
        next_month = first.replace(year=first.year + 1, month=1)
    else:
        next_month = first.replace(month=first.month + 1)
    last = next_month - timedelta(days=1)
    return first, last


def previous_month_bounds(as_of: date) -> Tuple[date, date]:
    """Return (first_day, last_day) of the month immediately before as_of's month."""
    first_this, _ = month_bounds(as_of)
    last_prev = first_this - timedelta(days=1)
    return month_bounds(last_prev)


def week_bounds(as_of: date) -> Tuple[date, date]:
    """Return (Monday, Sunday) of the ISO week containing as_of."""
    monday = as_of - timedelta(days=as_of.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def previous_week_bounds(as_of: date) -> Tuple[date, date]:
    monday, _ = week_bounds(as_of)
    prev_sunday = monday - timedelta(days=1)
    return week_bounds(prev_sunday)


def rolling_window(as_of: date, days: int) -> Tuple[date, date]:
    """Return (start, end) for a trailing N-day window ending on as_of (inclusive)."""
    return as_of - timedelta(days=days - 1), as_of


def period_label(start: date, granularity: str = "month") -> str:
    """Human-readable period label, e.g. '2024-12' or '2024-W49'."""
    if granularity == "month":
        return start.strftime("%Y-%m")
    if granularity == "week":
        return f"{start.isocalendar()[0]}-W{start.isocalendar()[1]:02d}"
    return start.isoformat()


def safe_pct_change(current: float, previous: float) -> float:
    """
    Percentage change with zero-division guard.
    Returns 0.0 if previous is 0 — avoids inf/-inf propagating into reports.
    """
    if previous == 0:
        return 0.0
    return round(100 * (current - previous) / abs(previous), 2)


def safe_ratio(numerator: float, denominator: float) -> float:
    """Division with zero-division guard, returns 0.0 instead of raising/NaN."""
    if denominator == 0:
        return 0.0
    return numerator / denominator
