# Atlas v0.6 — Sprint 6 Release Notes

## Summary
Sprint 6 delivers the FastAPI REST layer over the Sprint 5 analytics engine:
**8 Intelligence Hubs, 36 business endpoints**, all backed by real analytics
calculations — no fabricated or placeholder values anywhere in the API
surface.

## Intelligence Hubs (8/8, 36 endpoints)
Executive (3) · Revenue (3) · Growth (3) · Narrative (3) · Customer (7) ·
Product (7) · Operations (6) · Market (4)

Full endpoint-by-endpoint detail: [`frontend/contracts/api_contracts.md`](../../frontend/contracts/api_contracts.md)

## Key Capabilities
- Consistent `{data, meta, errors}` response envelope on every endpoint
- `X-API-Key` authentication on all business endpoints
- Centralized error handling with stable error codes
  (`INVALID_DATE_RANGE`, `INVALID_PARAMETER`, `NOT_FOUND`, `UNAUTHORIZED`,
  `DATA_UNAVAILABLE`, `VALIDATION_ERROR`, `INTERNAL_ERROR`)
- One narrow, approved analytics addition (Growth: `funnel_conversion`,
  `cac_by_channel`, `activation_rate`) — every other hub is pure
  orchestration over the existing Sprint 5 KPI registry, insight engine,
  decision engine, and anomaly engine
- Documented gaps instead of fabricated values where a capability doesn't
  exist (e.g. Market's `efficiency` endpoint explicitly labels LTV/CAC as a
  proxy, not a formally defined "Market Efficiency" KPI)

## Security & Configuration
- CORS `allow_origins` corrected to use the existing origin-list parsing
  (previously received a raw string, which Starlette matched via
  substring containment rather than exact origin comparison)
- `ATLAS_API_KEY` documented in `.env.example`
- Production startup now refuses to boot if `ATLAS_SECRET_KEY`,
  `JWT_SECRET_KEY`, or `ATLAS_API_KEY` are left at their insecure
  development default — development mode is unaffected

## Testing
**201/201 tests passing.** Two previously-stale Sprint 1 test assertions
(referencing environment-variable and config-class names that had since
changed) were corrected to match the current implementation — no
production behavior was altered to make them pass.

## Known Limitation
Live Docker/Docker Compose startup was not runtime-verified — no Docker
daemon is available in the environment this release was prepared in.
Static inspection of the `Dockerfile` and `docker-compose.yml` found no
issues (pinned base image, non-root user, real health checks, correct
service startup ordering), but this has not been confirmed by an actual
build/run. Recommended as the first verification step in an environment
with Docker available.
