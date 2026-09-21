"""
Atlas – Centralized Exception Handling

Registers FastAPI exception handlers so every error response — whether
raised deliberately (AtlasAPIError subclasses), a FastAPI validation
error, or an unhandled exception — comes back in the same envelope
shape as successful responses, per api_contracts.md:

    { "data": null, "errors": [{ "code": "...", "message": "..." }] }

This is the single place error responses are constructed. Route
handlers should never build an error JSONResponse by hand.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger

from backend.app.core.exceptions import AtlasAPIError


def _error_envelope(errors: list[dict]) -> dict:
    return {"data": None, "meta": None, "errors": errors}


def register_exception_handlers(app: FastAPI) -> None:
    """Call once from the application factory in main.py."""

    @app.exception_handler(AtlasAPIError)
    async def atlas_api_error_handler(request: Request, exc: AtlasAPIError) -> JSONResponse:
        logger.warning(f"{exc.code} on {request.method} {request.url.path}: {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_envelope([{"code": exc.code, "message": exc.message}]),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {
                "code": "VALIDATION_ERROR",
                "message": f"{'.'.join(str(loc) for loc in err['loc'][1:])}: {err['msg']}",
            }
            for err in exc.errors()
        ]
        logger.warning(f"Validation error on {request.method} {request.url.path}: {errors}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_envelope(errors),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(f"Unhandled exception on {request.method} {request.url.path}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_envelope(
                [{"code": "INTERNAL_ERROR", "message": "An unexpected error occurred."}]
            ),
        )
