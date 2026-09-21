"""
Atlas – Shared Query-Parameter Validation

Small helpers reused across multiple hub routers.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from backend.app.core.exceptions import InvalidDateRangeError, InvalidParameterError

VALID_GRANULARITIES = ("day", "week", "month")


def validate_date_range(start_date: Optional[date], end_date: Optional[date]) -> None:
    if start_date is not None and end_date is not None and start_date > end_date:
        raise InvalidDateRangeError("start_date must be before end_date")


def validate_granularity(granularity: str) -> str:
    if granularity not in VALID_GRANULARITIES:
        raise InvalidParameterError(
            f"granularity must be one of {VALID_GRANULARITIES}, got '{granularity}'"
        )
    return granularity
