# ============================================================
# Atlas – Digital Banking Intelligence Platform
# Backend Dockerfile
# ============================================================

FROM python:3.11-slim AS base

# Build metadata
LABEL maintainer="Atlas Team"
LABEL description="Atlas Digital Banking Intelligence Platform – API Server"
LABEL version="1.0"

# Environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# ─── System dependencies ──────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# ─── Python dependencies ──────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# ─── Application code ─────────────────────────────────────────────────────────
COPY . .

# ─── Non-root user ────────────────────────────────────────────────────────────
RUN addgroup --system atlas && adduser --system --group atlas
USER atlas

# ─── Health check ─────────────────────────────────────────────────────────────
# Uses ${PORT:-8000} to match whatever port the CMD below actually binds to —
# see the CMD comment for why this must stay in sync.
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:${PORT:-8000}/health').raise_for_status()"

EXPOSE 8000

# Shell-form CMD (not the previous JSON-array/exec-form) so ${PORT:-8000} is
# expanded by the shell at container start, not parsed as a literal string.
# Render (and similar PaaS hosts) assign a port dynamically via the PORT
# env var and require the app to bind to it; the app previously always
# bound to a hardcoded 8000 regardless of PORT, which would fail on such
# a host. Falls back to 8000 when PORT is unset, so local `docker run`
# and docker-compose usage (which map a host port to the container's
# fixed 8000) are unaffected. `exec` replaces the shell process with
# uvicorn so it still receives signals directly (e.g. SIGTERM on
# shutdown/redeploy), preserving the graceful-shutdown behavior
# exec-form CMD normally provides.
CMD exec uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 4
