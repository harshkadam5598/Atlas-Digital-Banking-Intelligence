# Atlas — Phase 1A Deployment Preparation

Follow-up to the Phase 1 Deployment Readiness Audit. This document
records exactly what changed to address the audit's findings, how each
change was validated, and what still requires a live PostgreSQL
instance or an actual deployment environment to verify. No hosting
provider has been selected and nothing has been deployed — this is
preparation only.

## 1. Database initialization (audit finding C1)

**Problem**: `docker-compose.yml`'s Postgres service mounted only
`sql/schema/` into `docker-entrypoint-initdb.d`. `sql/indexes/` and
`sql/views/` were never applied automatically. Per `sql/views/
01_analytics_views.sql`'s own header comment, the views are *"the only
thing the API layer queries"* — so a database brought up via
`docker-compose up` alone would start, but every API endpoint would
fail against a missing view.

**Fix**: `deployment/docker/docker-compose.yml` now mounts the whole
`sql/` directory (read-only) plus a new orchestration script,
`deployment/docker/init-db.sh`, into `docker-entrypoint-initdb.d`. The
script applies the existing SQL files — schema → indexes → views →
`dim_date` population → validation — in the exact same order already
used and documented by `scripts/db_init.sh`. **No SQL was duplicated
or rewritten**; the new script only runs `psql -f` against the existing
files.

**Verified through source inspection**: file order matches
`scripts/db_init.sh` exactly; the script is a direct translation of an
already-reviewed, already-used sequence into the
`docker-entrypoint-initdb.d` context.

**Not verified** (no PostgreSQL server or client is available in this
implementation environment): that the script actually executes
correctly inside a real Postgres container on first boot — the local-
socket connection pattern, `$POSTGRES_USER`/`$POSTGRES_DB` env-var
availability during init, and file permissions/mount behavior are all
standard for the official `postgres` image, but have not been run
end-to-end here. **This must be verified against a real
`docker-compose up` before being relied on.**

`scripts/db_init.sh` itself is unchanged and remains the correct manual
path for a non-Docker Postgres instance.

## 2. Frontend SPA deployment preparation (audit finding C3)

**Problem**: the frontend uses React Router's `BrowserRouter`
(client-side routing). Without a rewrite rule, a static host would
404 on direct navigation or a refresh at any route other than `/`
(e.g. `/revenue`, `/operations`).

**Fix**: added two dormant, provider-specific config files — neither
is used unless that specific host is chosen, and no hosting decision
has been made:
- `frontend/public/_redirects` — honored by Netlify and Cloudflare
  Pages (identical format for both): `/* /index.html 200`
- `frontend/vercel.json` — a `rewrites` rule for Vercel

**Verified through local execution**: ran `npm run build` and
confirmed `_redirects` is copied verbatim into `dist/` (Vite copies
everything under `public/` to the build output root). `vercel.json`
is a static config file read by Vercel's build system, not something
this environment can execute-test without a Vercel deployment.

**Not addressed** (out of this phase's explicit scope): no frontend
Dockerfile or nginx config was added. That remains audit finding C2 —
deferred until a hosting architecture (containerized vs. static host)
is chosen, since the two paths need different solutions.

**No secrets were added or hardcoded.** `VITE_API_KEY` in
`frontend/.env.example` remains a placeholder. The architectural
concern that any real value set there would be publicly visible in the
compiled JS bundle (audit finding D1) is **not resolved by this
change** — see the Phase 1 audit and the authentication note in the
implementation report for this phase.

## 3. Docker build context (audit finding D5)

**Problem**: no `.dockerignore` existed. Building the backend image
with `context: ../..` (repo root, per `docker-compose.yml`) would
include `frontend/node_modules` (221 MB), `.git`, and other irrelevant
content in the build context.

**Fix**: added a root-level `.dockerignore`. Confirmed by inspection
that nothing it excludes is read by the backend at build or run time —
the app imports only `backend/` and `analytics/`; `data/` is
volume-mounted at runtime rather than baked into the image; `docs/`
and `notebooks/` are referenced only in code comments/docstrings as
human-readable pointers, never read as files by the running
application.

**Verified through source inspection** (grep across `backend/app/` for
any reference to `docs/`, `notebooks/`, or `data/*.csv` as a file
path — none found). **Not verified**: an actual `docker build` was not
run in this environment (no Docker daemon available), so build-time
behavior itself is unverified.

## 4. Production secret guard (audit finding D3)

**Problem**: the startup guard in `backend/app/main.py` that refuses
to boot in production with default secrets checked
`ATLAS_SECRET_KEY`, `JWT_SECRET_KEY`, and `ATLAS_API_KEY`, but not
`POSTGRES_PASSWORD` — a production deployment could run on the
default database password without any warning.

**Fix**: extracted the check into a standalone function,
`check_production_secrets()`, and added `POSTGRES_PASSWORD` (with its
own default sentinel, `"atlas_password"`, distinct from the other
three secrets' shared default) to the set of checks. Behavior is
otherwise unchanged: the guard still only runs when
`settings.is_production` is true, still only logs secret *names*
(never values), and still raises the same `RuntimeError` shape.

**Verified through local execution**:
- `check_production_secrets()` was run directly against the real
  `AtlasSettings` object with default (unconfigured) values — all
  four secrets, including `POSTGRES_PASSWORD`, were correctly
  detected as insecure defaults.
- Confirmed `settings.is_production` is `False` by default, so the
  guard remains fully inert in the normal development workflow —
  existing behavior for developers is unchanged.
- Added 7 new unit tests
  (`tests/unit/test_production_secret_guard.py`) covering each
  secret individually, multiple-defaults-at-once, and that the two
  different default sentinels don't cross-contaminate each other's
  detection.
- Full offline test suite re-run after the change: **208 passed**
  (the previous 201 + these 7 new tests), confirming no regression.

## 5. Redis and JWT — status review (audit finding D7)

Per the audit and re-confirmed here: neither is used anywhere outside
`backend/app/core/config.py` (which only defines their settings) and,
for JWT, `backend/app/main.py` (which includes `JWT_SECRET_KEY` in the
production secret guard, purely as a precaution in case it's adopted
later, not because anything currently authenticates with it).

**Neither has been removed.** Per this phase's instructions, they are
documented here as **reserved, optional deployment components**:

- **Redis**: provisioned in `docker-compose.yml` for a KPI-caching
  layer that was never built. Not required to run Atlas today. A
  minimal deployment can omit the Redis service entirely without
  losing any current functionality — but doing so is a deployment
  *decision* to make later, not something this phase changed.
- **JWT**: `JWTSettings` models a future user-authentication build-out
  that doesn't exist yet. The only real authentication today is the
  single static `X-API-Key` header (see `backend/app/core/security.py`).
  JWT settings are inert configuration, not a security control.

## 6. Remaining manual steps

A full local or deployed bring-up still requires running these in
order (unchanged from the audit — no single orchestrated script exists
yet, and adding one was not in this phase's scope):

1. `docker-compose -f deployment/docker/docker-compose.yml up -d postgres redis`
   (or `up -d postgres` alone, if Redis is omitted per §5)
2. Confirm `init-db.sh` completed successfully via `docker logs atlas_postgres`
   — **this is the step that is not yet verified against a real Postgres instance**
3. `python -m etl.extractors.pipeline_orchestrator` (sample or full scale)
4. `python -m etl.pipeline`
5. Start the API (`uvicorn backend.app.main:app` or the `api` compose service)
6. Build and deploy the frontend to whichever static host is eventually
   chosen, with `VITE_API_BASE_URL` pointed at the deployed backend

## 7. What still requires a real PostgreSQL instance or a deployment environment

- Whether `init-db.sh` actually runs successfully end-to-end inside the
  official `postgres:16-alpine` image's init sequence
- Whether `sql/validation/sprint2_validation.sql`'s `RAISE NOTICE`/
  `RAISE WARNING` output is visible and useful in `docker logs` as
  intended
- An actual `docker build` of the backend image (build succeeding,
  final image size, `.dockerignore` behavior)
- The frontend rewrite configs' real behavior once actually deployed
  to Netlify, Cloudflare Pages, or Vercel
- The full-scale (500,000-customer) ETL run's real time and memory
  footprint (unrelated to this phase's changes, but still an open
  question from the Phase 1 audit)
