<div align="center">

# Atlas
### Digital Banking Intelligence Platform

*A full-stack analytics platform demonstrating product, growth, and financial intelligence for a digital banking business*

![Python](https://img.shields.io/badge/python-3.11+-blue)
![PostgreSQL](https://img.shields.io/badge/postgresql-16-blue)
![FastAPI](https://img.shields.io/badge/fastapi-0.111-green)
![React](https://img.shields.io/badge/react-19-61DAFB)
![Tests](https://img.shields.io/badge/backend%20tests-208%2F208%20passing-brightgreen)

</div>

---

## What is Atlas?

Atlas is a full-stack Digital Banking Intelligence Platform: a PostgreSQL data
warehouse, a Python analytics engine, a FastAPI backend, and a React
frontend, built around a synthetic (not real customer) digital banking
dataset. It's a portfolio project demonstrating end-to-end data
engineering, analytics, and product-analytics-style dashboard design.

## Key Features — 7 Intelligence Hubs + Executive Narrative

- **Executive Command Center** — company-wide KPIs, health-score
  breakdown, and risk & alerts in one view
- **Customer Intelligence Hub** — activity, retention, churn, and
  customer value (ARPU/CLV/LTV-CAC)
- **Growth Intelligence Hub** — signup funnel, CAC by channel,
  activation trend
- **Product Intelligence Hub** — product adoption, stickiness,
  cross-sell, feature adoption
- **Revenue Intelligence Hub** — revenue summary, trend, and forecast
  with confidence range
- **Operational Intelligence Hub** — KYC, fraud, support, and
  transaction health, with real anomaly detection
- **Market Intelligence Hub** — geographic revenue and growth,
  acquisition-efficiency proxy
- **Executive Narrative Engine** — auto-generated insights,
  recommendations, and risk summaries, surfaced inside the Executive
  Command Center

Every figure shown in the UI is computed from the underlying dataset —
there are no hardcoded or placeholder metrics.

## Technology Stack

**Backend**: Python, FastAPI, SQLAlchemy, pandas, NumPy, scikit-learn, statsmodels
**Frontend**: React 19, TypeScript, Vite, Recharts, React Router
**Database**: PostgreSQL 16
**Data**: Synthetic dataset generated via a custom ETL pipeline

## Architecture

```
React + Vite SPA  →  FastAPI REST API (36 endpoints)  →  PostgreSQL 16
                         ↑
                  ETL pipeline loads a synthetic
                  banking dataset into the warehouse
```

The frontend calls the backend via `fetch()` with an `X-API-Key`
header. The backend reads from a set of analytics views built on top
of a star-schema warehouse (dimension + fact tables).

## Repository Structure

```
backend/        FastAPI application (routes, services, core config)
analytics/      KPI, forecasting, anomaly, and insight engines
etl/            Synthetic data generation, transform, and load pipeline
sql/            Schema, indexes, analytics views, validation scripts
frontend/       React + TypeScript + Vite application
tests/          Backend unit and analytics tests
scripts/        Local setup and database initialization scripts
deployment/     Dockerfile, docker-compose, and init scripts
docs/           Architecture, business, ETL, frontend, and deployment docs
```

## Local Setup

**Backend**
```bash
pip install -r requirements.txt
cp .env.example .env               # edit values as needed
docker-compose -f deployment/docker/docker-compose.yml up -d postgres
bash scripts/db_init.sh            # schema + indexes + views
python -m etl.extractors.pipeline_orchestrator --sample 2000 --force
python -m etl.pipeline
uvicorn backend.app.main:app --reload   # http://localhost:8000/docs
```

**Frontend**
```bash
cd frontend
npm install
cp .env.example .env.local         # set VITE_API_BASE_URL / VITE_API_KEY
npm run dev                        # http://localhost:5173
```

## Testing Status

- **Backend**: 208/208 tests passing (`pytest tests/analytics/ tests/unit/`)
  — analytics engines and foundational checks. No API-route-level or
  integration tests exist yet.
- **Frontend**: builds and lints clean (`npm run build`, `npm run lint`),
  no automated frontend test suite yet.

## Known Limitations

- Sample dataset only (2,000 customers). The full 500,000-customer
  scale is supported by the ETL pipeline but has not been run or
  validated in this environment.
- No automated frontend or API-integration tests.
- Authentication is a single static API key. Because the frontend is a
  static site, this key is compiled into the public JS bundle and is
  visible to anyone who inspects it — it is not a real secret once
  deployed, only a coarse check that requests came from the frontend.
  Acceptable for a demo serving synthetic data only, not a production
  auth system.
- Redis and JWT are configured but not currently used by the application.

## Deployment Status

Atlas is **not currently deployed**. The backend and frontend are
prepared for deployment (Docker configuration, environment variable
handling, and a `PORT`-aware startup command for platforms like
Render), but no live public instance exists yet. See `docs/deployment/`
for the deployment readiness work completed so far.

## Screenshots

_Screenshots to be added._
