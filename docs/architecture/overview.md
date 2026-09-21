# Atlas Architecture Overview

## System Design

Atlas is built as a layered analytics platform where each layer has a single responsibility:

```
┌─────────────────────────────────────────────────────┐
│                  Executive Users                     │
│         (CEO, CPO, CGO, Analysts)                   │
└───────────────────────┬─────────────────────────────┘
                        │ HTTPS
┌───────────────────────▼─────────────────────────────┐
│              Atlas Web Application                   │
│    (Executive Command Center + 7 Intelligence Hubs) │
└───────────────────────┬─────────────────────────────┘
                        │ REST API
┌───────────────────────▼─────────────────────────────┐
│                  API Layer (FastAPI)                 │
│      /executive  /customer  /growth  /revenue       │
│      /product    /operations  /market  /narrative   │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│               Analytics Engine                       │
│   Descriptive → Diagnostic → Predictive → Prescriptive│
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│          PostgreSQL Data Warehouse                   │
│    Raw Zone → Staging Zone → Analytics Zone         │
│    Dimensions: customer, product, date, country     │
│    Facts: transactions, journeys, events, revenue   │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│              ETL Pipeline                            │
│          Extract → Transform → Load                  │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│           Synthetic Data Engine                      │
│   500K Customers | 5M Transactions | 10M Events     │
│              3 Years Historical Data                 │
└─────────────────────────────────────────────────────┘
```

## Key Architecture Decisions

### 1. Star Schema Data Warehouse
**Decision:** PostgreSQL with star schema (dimensions + facts)
**Rationale:** Optimized for analytical queries (GROUP BY, JOINs on dimension keys). Enables slice-and-dice by customer segment, date, country, product without complex query rewrites.

### 2. Layered Data Zones
**Decision:** Raw → Staging → Analytics zones within PostgreSQL
**Rationale:** Follows modern analytics engineering (dbt-style) separation of concerns. Raw data is immutable, staging applies business rules, analytics exposes KPI-ready tables.

### 3. Python + FastAPI Backend
**Decision:** Python with FastAPI for the API layer
**Rationale:** FastAPI provides OpenAPI docs automatically, async support, and Pydantic validation. Python covers both the data science layer (pandas, sklearn) and API layer in one language.

### 4. Pydantic Settings for Config
**Decision:** pydantic-settings for environment config
**Rationale:** Type-safe, validates required variables at startup, prevents silent misconfiguration. Fails loudly if DATABASE_URL is missing rather than failing silently at query time.

### 5. Modular API Routes
**Decision:** One FastAPI router per intelligence hub
**Rationale:** Maps directly to Atlas's 8 modules. Each module team can work independently. Sprint 6 assembles the routers.

## Sprint Delivery Sequence

| Sprint | Layer Delivered |
|--------|----------------|
| 1 | Foundation (this document) |
| 2 | PostgreSQL schema + warehouse |
| 3 | Synthetic data engine (500K+ customers) |
| 4 | ETL pipelines (Raw → Analytics) |
| 5 | Analytics engine + KPIs |
| 6 | REST API layer |
| 7 | Web application (all 8 hubs) |
| 8 | Deployment + public URL |
