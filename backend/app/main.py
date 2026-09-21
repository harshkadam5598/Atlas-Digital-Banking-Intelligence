"""
Atlas – Digital Banking Intelligence Platform
FastAPI Application Entry Point

This is the root of the Atlas API server. It:
- Initializes the application
- Registers all routers
- Configures middleware
- Handles startup/shutdown lifecycle
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from loguru import logger

from backend.app.core.config import settings
from backend.app.core.database import verify_connection
from backend.app.core.error_handlers import register_exception_handlers
from backend.app.core.logging import configure_logging

# ─── Production Secret Guard ──────────────────────────────────────────────────
#
# Extracted (Phase 1A) from lifespan() into a standalone, synchronous function
# purely so it can be unit-tested without mocking an async context manager or
# a live database — behavior is unchanged from the original inline version.
#
# Refuses to start in production with any secret still at its known,
# source-visible insecure default. Development/staging are unaffected — the
# caller only invokes this when settings.is_production. POSTGRES_PASSWORD is
# checked alongside the original three (ATLAS_SECRET_KEY, JWT_SECRET_KEY,
# ATLAS_API_KEY) — a gap identified in the Phase 1 Deployment Readiness Audit,
# since a production deploy could previously run on default DB credentials
# without the startup guard noticing. It has its own default sentinel
# ("atlas_password", from DatabaseSettings) rather than sharing the other
# three secrets' shared default string. Only secret *names* are ever
# returned/logged, never values.

_INSECURE_DEFAULT = "insecure-dev-key-change-in-production"
_INSECURE_DB_PASSWORD_DEFAULT = "atlas_password"


def check_production_secrets(app_settings) -> list[str]:
    """Return the names of any secret still at its insecure default value."""
    insecure = {
        "ATLAS_SECRET_KEY": (app_settings.secret_key, _INSECURE_DEFAULT),
        "JWT_SECRET_KEY": (app_settings.jwt.secret_key, _INSECURE_DEFAULT),
        "ATLAS_API_KEY": (app_settings.api_key, _INSECURE_DEFAULT),
        "POSTGRES_PASSWORD": (app_settings.db.password, _INSECURE_DB_PASSWORD_DEFAULT),
    }
    return [name for name, (value, default) in insecure.items() if value == default]


# ─── Lifespan ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown lifecycle.
    Startup: verify DB, initialize caches, log ready state.
    Shutdown: flush logs, close connections gracefully.
    """
    # Startup
    configure_logging()
    logger.info(f"Starting Atlas v{settings.version} [{settings.env}]")

    if settings.is_production:
        still_default = check_production_secrets(settings)
        if still_default:
            logger.critical(
                f"Refusing to start in production with insecure default "
                f"secret(s): {', '.join(still_default)}. Set a real value "
                f"for each before deploying to production."
            )
            raise RuntimeError(
                f"Insecure default secret(s) in production: {', '.join(still_default)}"
            )

    if not verify_connection():
        logger.critical("Database unreachable at startup. Exiting.")
        raise RuntimeError("Cannot connect to PostgreSQL. Check DB_HOST, DB_PORT, DB_NAME.")

    logger.info("Atlas API ready to serve requests.")
    yield

    # Shutdown
    logger.info("Atlas API shutting down gracefully.")


# ─── Application Factory ──────────────────────────────────────────────────────

def create_application() -> FastAPI:
    """
    Factory function that builds and configures the FastAPI app.
    Separating this from module-level instantiation enables clean testing.
    """
    app = FastAPI(
        title="Atlas – Digital Banking Intelligence Platform",
        description=(
            "Enterprise-grade analytics platform providing 360-degree visibility "
            "into customer behavior, product performance, revenue, growth efficiency, "
            "and operational health for modern digital banking organizations."
        ),
        version=settings.version,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ─── Middleware ───────────────────────────────────────────────────────────

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # ─── Centralized Error Handling ───────────────────────────────────────────
    register_exception_handlers(app)

    # ─── Hub Routers ──────────────────────────────────────────────────────────
    # All eight Sprint 6 hubs implemented and validated.
    from backend.app.api.v1.executive.routes import router as executive_router
    from backend.app.api.v1.customer.routes import router as customer_router
    from backend.app.api.v1.growth.routes import router as growth_router
    from backend.app.api.v1.market.routes import router as market_router
    from backend.app.api.v1.narrative.routes import router as narrative_router
    from backend.app.api.v1.operations.routes import router as operations_router
    from backend.app.api.v1.product.routes import router as product_router
    from backend.app.api.v1.revenue.routes import router as revenue_router

    for hub_router in (
        executive_router,
        customer_router,
        growth_router,
        market_router,
        narrative_router,
        operations_router,
        product_router,
        revenue_router,
    ):
        app.include_router(hub_router, prefix=settings.api_prefix)

    # ─── Health Check ─────────────────────────────────────────────────────────

    @app.get("/health", tags=["System"])
    async def health_check():
        """System health probe. Used by deployment platforms and load balancers."""
        db_ok = verify_connection()
        return JSONResponse(
            status_code=200 if db_ok else 503,
            content={
                "status": "healthy" if db_ok else "degraded",
                "version": settings.version,
                "environment": settings.env,
                "database": "connected" if db_ok else "unreachable",
            }
        )

    # ─── Frontend (optional, single-URL mode) ─────────────────────────────────
    # If a built frontend exists at frontend/dist, serve it from this same
    # process so the whole app is reachable at one URL (e.g. http://localhost:8000)
    # instead of running separate frontend/backend dev servers. Purely additive:
    # if the frontend hasn't been built — API-only use, tests, or a split
    # deployment where the frontend is hosted elsewhere (e.g. Cloudflare Pages)
    # — nothing here changes, and the root path keeps its existing JSON response.
    frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"

    if frontend_dist.is_dir():
        api_prefix_segment = settings.api_prefix.lstrip("/")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_frontend(full_path: str):
            """Serve the built SPA for any path that isn't a real API/system route."""
            if full_path.startswith(api_prefix_segment) or full_path in (
                "health", "docs", "redoc", "openapi.json",
            ):
                raise HTTPException(status_code=404)
            candidate = frontend_dist / full_path
            if full_path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(frontend_dist / "index.html")
    else:
        @app.get("/", tags=["System"])
        async def root():
            """API root — confirms Atlas is running."""
            return {
                "platform": "Atlas – Digital Banking Intelligence Platform",
                "version": settings.version,
                "environment": settings.env,
                "docs": "/docs",
                "health": "/health",
            }

    return app


# ─── App Instance ─────────────────────────────────────────────────────────────

app = create_application()
