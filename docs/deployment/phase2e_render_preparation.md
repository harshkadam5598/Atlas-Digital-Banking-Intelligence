# Atlas — Phase 2E: Backend Deployment Preparation

Preparation only. No deployment was attempted, no account was created,
no results were simulated. This phase fixes what Phase 2D's research
identified as a real blocker, reviews the rest of the production
configuration, and hands off a concrete checklist for the one thing
only a human with real Render account access can do.

## 1. Objective

Get the backend genuinely ready for a **user-executed** Render
deployment: fix the one known configuration blocker, verify everything
else that can be verified without deployment access, and produce a
checklist precise enough that the manual Render steps require no
guesswork.

## 2. Phase 2D Blocker Summary

Phase 2D confirmed, via a direct network test (`curl` to `render.com`
and `api.render.com` both returned `403` from this environment's
egress proxy), that this sandbox cannot reach Render's infrastructure
and has no account-creation or browser-automation tooling. That
constraint is unchanged and this phase does not attempt to work around
it — deployment itself still requires you. What Phase 2D *did*
establish through documentation research (not deployment) was a real
gap: **the Dockerfile hardcoded port 8000**, while Render assigns a
port dynamically via a `PORT` environment variable and expects the app
to bind to it. This phase fixes that.

## 3. Port Configuration Findings

**Root cause**: the Dockerfile's `CMD` was in JSON-array ("exec")
form:
```
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```
Exec-form `CMD` runs the process directly, with **no shell
involved** — so even if `$PORT` were inserted as a literal array
element, Docker would never expand it; uvicorn would receive the
literal four-character string `${PORT}` as its `--port` value and fail
to start. The fix requires shell-form `CMD` for the variable
substitution to happen at all.

Separately confirmed: `backend/app/core/config.py`'s
`ServerSettings.port` field (env var `ATLAS_PORT`) is **not read
anywhere in the actual startup path** — it's decorative/unused
configuration, disconnected from what port the Dockerfile actually
binds to. This is a pre-existing inconsistency, not something this
phase's fix touches (it's unrelated to the Render blocker and outside
this phase's scope to correct — noted here for visibility only).

## 4. Changes Made

**File**: `deployment/docker/Dockerfile` (only file with logic changes this phase)

Two lines changed:

1. **`CMD`** — changed from exec-form (hardcoded `8000`) to shell-form:
   ```
   CMD exec uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 4
   ```
   - `${PORT:-8000}`: binds to whatever the `PORT` environment variable
     is set to; falls back to `8000` if it's unset (preserving exact
     previous behavior for local `docker run`/`docker-compose`, neither
     of which set `PORT`).
   - Leading `exec`: replaces the shell process with uvicorn itself, so
     uvicorn becomes PID 1 and receives signals (e.g. `SIGTERM` on
     redeploy/shutdown) directly — this specifically preserves the
     graceful-shutdown behavior that plain exec-form `CMD` normally
     provides, which switching to shell-form would otherwise weaken.

2. **`HEALTHCHECK`** — updated to target the same dynamic port
   (`${PORT:-8000}`) instead of a hardcoded `8000`, so Docker's own
   internal health probe still checks the port the app is actually
   listening on. (This line was already shell-form — a bare string,
   not a JSON array — so no form change was needed here, only the
   hardcoded value.)

**Nothing else was changed.** `docker-compose.yml` (from Phase 1A) was
reviewed and needs no change: its `api` service doesn't set a `PORT`
env var, so it correctly continues to fall back to `8000`, matching its
existing `${ATLAS_PORT:-8000}:8000` host-port mapping exactly as
before.

## 5. Environment-Variable Reference

| Variable | Required? | Default | Notes |
|---|---|---|---|
| `PORT` | Set automatically by Render | `8000` (local fallback) | **Do not set manually** on Render — the platform injects this itself |
| `ATLAS_ENV` | Yes, for production | `development` | Must be `production` to activate the secret guard |
| `ATLAS_SECRET_KEY` | **Yes, before production** | insecure placeholder | Guard refuses to start in production if left default |
| `ATLAS_API_KEY` | **Yes, before production** | insecure placeholder | Same as above; also the value the deployed frontend's `VITE_API_KEY` must match |
| `JWT_SECRET_KEY` | **Yes, before production** | insecure placeholder | Guard-checked even though JWT auth itself is unused (see Phase 1A) |
| `POSTGRES_PASSWORD` | **Yes, before production** | insecure placeholder | Guard-checked since Phase 1A |
| `POSTGRES_HOST` / `PORT` / `DB` / `USER` | Yes | local defaults | Must point at the real Render Postgres instance |
| `ATLAS_CORS_ORIGINS` | Yes, before public use | `localhost` only | Must be set to the real deployed frontend's origin |
| `ATLAS_DEBUG` | Optional | `true` | Not wired to any behavior found in this codebase beyond being read (see Phase 1 audit) — leave default unless a reason emerges |
| `ATLAS_LOG_LEVEL` | Optional | `INFO` | |
| `REDIS_*` | Optional / not required | — | Redis is entirely unused by the running application (Phase 1 audit, re-confirmed) — can be omitted from the Render service entirely |
| `DATA_*` / `ANALYTICS_*` / `ETL_*` | Not needed at API runtime | — | Only relevant to the separate, locally-run ETL step, not the deployed API process |

## 6. Security Considerations

- No actual secret values appear anywhere in this document or were
  transmitted anywhere — every value above is either a placeholder
  name or the publicly-known insecure default already in
  `.env.example`.
- The production secret guard (`check_production_secrets()`, Phase 1A)
  will **refuse to start** if `ATLAS_ENV=production` and any of the
  four secret-bearing variables above are left at their defaults —
  confirmed still working in this phase's validation (section 7).
- Unchanged from Phase 1/2A/2B: the frontend's `VITE_API_KEY` is
  compiled into the public JS bundle at build time. Whatever value is
  set there is visible to anyone inspecting the deployed site's source.
  This phase does not change or resolve that; it's an architecture
  decision still pending (Phase 2A §D).

## 7. Local Validation Results

Docker itself remains unavailable in this environment (confirmed again
this phase — no change from Phase 1B/1A/2D). Everything below was
verified without it, and is explicitly labeled by method.

**Verified through direct shell simulation** (proving the exact
substitution logic Docker's shell-form CMD would perform):
```
$ sh -c 'echo ${PORT:-8000}'
8000
$ PORT=10000 sh -c 'echo ${PORT:-8000}'
10000
```

**Verified through real local execution** (running the literal
resulting command outside Docker, against a real local PostgreSQL 16
instance):
```
$ POSTGRES_HOST=localhost ... PORT=10000 sh -c \
    'exec uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1'
...
INFO:     Uvicorn running on http://0.0.0.0:10000
$ curl http://127.0.0.1:10000/health          → HTTP 200
$ curl --max-time 2 http://127.0.0.1:8000/health → connection refused (000)
```
This confirms the app binds to the **dynamic** port and *not* the old
hardcoded 8000 when `PORT` is set — the exact Render scenario.

Re-tested with `PORT` unset:
```
$ uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --workers 1
...
INFO:     Uvicorn running on http://0.0.0.0:8000
$ curl http://127.0.0.1:8000/health → HTTP 200
```
Confirms the fallback preserves exact prior local behavior.

**Verified through local execution — application-level checks**:
- `from backend.app.main import create_application; create_application()` → imports cleanly, 42 routes registered
- `check_production_secrets(settings)` against real default settings → correctly returns all four insecure-default names (`['ATLAS_SECRET_KEY', 'JWT_SECRET_KEY', 'ATLAS_API_KEY', 'POSTGRES_PASSWORD']`), confirming the guard is unaffected by this phase's changes
- Full offline test suite: `pytest tests/analytics/ tests/unit/` → **208 passed**, no regressions

**Not verified (requires Docker, unavailable in this environment)**:
- An actual `docker build` of the updated Dockerfile
- The `HEALTHCHECK` directive's real behavior inside a running container
- Any Render-specific runtime behavior

## 8. User-Executed Render Deployment Checklist

Everything below requires your direct action — none of it can be done from this environment.

1. **Account/billing — verify yourself first.** Phase 2D found Render's own pricing page mentions a "$1 security-check transaction" in a context that wasn't clearly free-tier-specific. Before signing up, check Render's actual current sign-up flow yourself to see whether a card is requested. If one is, decide whether that's acceptable before proceeding — I cannot resolve this ambiguity for you.
2. **Connect your repository** to Render via GitHub (or your Git host) through Render's dashboard.
3. **Service type**: "Web Service," pointed at the `deployment/docker/Dockerfile` (Render can build directly from a Dockerfile — no separate build command needed since the Dockerfile handles `pip install`).
4. **Build command**: not needed separately — Docker builds handle this via the Dockerfile itself.
5. **Start command**: not needed separately — the Dockerfile's `CMD` (now fixed) handles this.
6. **Environment variables**: set every "Required" row from the table in section 5 to real, unique, random values via Render's dashboard environment-variable UI — never in a committed file. Do **not** set `PORT` yourself; Render sets it.
7. **Database**: create a Render Postgres instance (or use Neon/Supabase per Phase 2B's research) and point `POSTGRES_HOST`/`PORT`/`DB`/`USER`/`PASSWORD` at it. Run the Phase 1B-verified initialization (`deployment/docker/init-db.sh`'s sequence, or `scripts/db_init.sh` directly) against it, then load the sample-scale dataset via the Phase 2C-verified ETL commands.
8. **CORS origin**: set `ATLAS_CORS_ORIGINS` to your eventual deployed frontend's real URL once you know it (or a placeholder you'll update, understanding the frontend won't work until this is correct).
9. **API key**: set `ATLAS_API_KEY` to a real random value; this same value must later be set as the frontend's `VITE_API_KEY` at its build time.
10. **Health-check endpoint**: configure Render to use `/health` as its health-check path.
11. **First-deployment verification**: after Render reports the service live, check `https://<your-service>.onrender.com/health` returns `{"status":"healthy","database":"connected"}`, then test one authenticated endpoint with your real API key.
12. **Cost control**: to stop incurring any usage or avoid surprise charges, use Render's dashboard to **suspend or delete the service** directly (Render's own free-tier web services don't bill by default, but any database or upgraded resource you attach might — check each resource's own settings). Do this immediately if you decide not to continue.

## 9. Unverified Items

- Whether Render's sign-up flow actually requests a card (Phase 2D's finding — still unresolved, needs your direct check)
- Actual Docker build success/failure and final image size for the updated Dockerfile
- Real Render runtime behavior: cold-start timing, actual memory ceiling enforcement, actual free-tier compute specs (Phase 2D found Render's free compute plan's exact RAM/CPU figure wasn't stated in the specific docs pages retrieved)
- Whether any other configuration issue exists beyond the port fix — this phase reviewed configuration statically and via local execution, not via an actual Render deployment

## 10. Recommended Next Step

The backend's known blocker is now fixed and validated as thoroughly as
is possible without Docker or Render access. The next real step is
Phase 2D's original recommendation, now unblocked on the code side: you
perform the account-level sign-up and initial service creation
yourself, following the checklist in section 8, and share back the
resulting logs/URL/errors — at that point I can help verify `/health`,
review real logs, and troubleshoot, since interpreting results you
provide doesn't require me to have direct network access to Render.

---

## Validation Summary

**Commands run**:
```
sh -c 'echo ${PORT:-8000}'                              # → 8000
PORT=10000 sh -c 'echo ${PORT:-8000}'                    # → 10000
uvicorn ... --port ${PORT:-8000} (PORT=10000, real run)  # bound to :10000, /health → 200
uvicorn ... --port 8000 (PORT unset, real run)           # bound to :8000, /health → 200
python -c "from backend.app.main import create_application; create_application()"
python -c "... check_production_secrets(settings) ..."
python -m pytest tests/analytics/ tests/unit/ -q
```

**Results**: all as described in section 7 — port fix behaves correctly
in both branches, app imports cleanly, secret guard unaffected and
correct, 208/208 tests pass.

**Files created**: `docs/deployment/phase2e_render_preparation.md`
**Files modified**: `deployment/docker/Dockerfile` only

**Remaining limitations**: no Docker daemon or Render network access in
this environment (unchanged since Phase 1B/2D) — this phase's
validation is as thorough as locally possible but does not constitute
proof the Dockerfile builds or runs correctly inside an actual
container, only that the underlying command and substitution logic is
correct. **Render compatibility and production readiness are not
claimed.**
