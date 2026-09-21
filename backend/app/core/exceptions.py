"""
Atlas – Centralized API Exceptions

Route handlers and services raise these instead of building error
responses inline. Each carries an HTTP status and a stable `code` string
that matches the contract's error shape:

    { "data": null, "errors": [{ "code": "...", "message": "..." }] }

Registered handlers in backend/app/main.py catch these (and unhandled
exceptions) and translate them into that envelope — see
backend/app/core/error_handlers.py.
"""

from __future__ import annotations

from typing import Optional


class AtlasAPIError(Exception):
    """Base class for all Atlas API errors. Carries an HTTP status + code."""

    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, *, code: Optional[str] = None, status_code: Optional[int] = None):
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        super().__init__(message)


class InvalidDateRangeError(AtlasAPIError):
    """start_date is after end_date, or a date param is malformed."""

    status_code = 400
    code = "INVALID_DATE_RANGE"


class InvalidParameterError(AtlasAPIError):
    """A query parameter failed validation beyond FastAPI's type coercion."""

    status_code = 400
    code = "INVALID_PARAMETER"


class ResourceNotFoundError(AtlasAPIError):
    """A named resource (KPI, cohort, segment, etc.) does not exist."""

    status_code = 404
    code = "NOT_FOUND"


class UnauthorizedError(AtlasAPIError):
    """Missing or invalid API credential."""

    status_code = 401
    code = "UNAUTHORIZED"


class DataUnavailableError(AtlasAPIError):
    """The analytics engine could not produce a result (e.g. empty dataset)."""

    status_code = 503
    code = "DATA_UNAVAILABLE"
