# Atlas — Phase 2D: Backend-Only Deployment Trial

**Status: BLOCKED — deployment could not be attempted.** This is a
blocker report, not a deployment result. Nothing was deployed, no
account was created, no billing action occurred, no secrets were
transmitted anywhere.

## Why This Is a Blocker Report, Not a Deployment Result

Two independent, verified constraints make actual deployment to Render
impossible from this environment:

1. **No network path to Render's infrastructure.** Direct test:
   ```
   $ curl -s -o /dev/null -w "%{http_code}" https://render.com
   403
   $ curl -s -o /dev/null -w "%{http_code}" https://api.render.com
   403
   ```
   Both requests were rejected by this environment's network egress
   proxy — `render.com` and `api.render.com` are not on the small
   allow-list of domains this sandbox can reach (pypi, npm, GitHub, and
   a handful of others). This is a hard technical block, not a policy
   judgment call.
2. **No account-creation or browser-automation capability.** Even with
   network access, creating a Render account, connecting a Git
   provider, and configuring a service through Render's dashboard or
   API requires interactive sign-up and OAuth-style authorization that
   no tool available in this session can perform. There is no Render
   MCP connector configured, no browser tool, and no existing Render
   credential to act on the user's behalf.

Per this phase's own instructions — *"If deployment cannot proceed
because account access, billing, or infrastructure is unavailable, do
not guess or simulate results. Produce a blocker report instead"* —
I stopped here rather than fabricate startup logs, response times, or
memory numbers for a service that was never actually created.

**What this means practically**: deploying to Render is something
**you** would need to do directly (Render's own dashboard, connecting
your GitHub account, clicking through the free-tier service creation
flow) — I cannot do it on your behalf from this environment. I can
prepare everything up to that point (which this report does) and can
help interpret results, troubleshoot logs, or adjust configuration
once you've done the account-level steps that require a human with
real account access.

## What Was Completed (everything possible without deployment access)

### 1. Pre-Deployment Review (repository inspection)

- **Git status**: clean of any tracked real `.env` file; confirmed via
  `git ls-files | grep -E "\.env$"` → no matches. Current working-tree
  changes are limited to the already-reviewed Phase 1A–2C artifacts
  (docs, `.dockerignore`, `requirements.txt`'s `tqdm` addition,
  `deployment/docker/init-db.sh`, the ETL-regenerated JSON/checkpoint
  files from Phase 2C, and `tests/unit/test_production_secret_guard.py`).
  No credentials, keys, or passwords are present in any tracked or
  newly-created file — confirmed by inspection, not assumed.
- **Start command** (from `deployment/docker/Dockerfile`):
  ```
  CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
  ```
- **Required environment variables** (from `backend/app/core/config.py`,
  cross-checked against `.env.example`): `POSTGRES_HOST`,
  `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`,
  `ATLAS_SECRET_KEY`, `ATLAS_API_KEY`, `JWT_SECRET_KEY`,
  `ATLAS_CORS_ORIGINS`, `ATLAS_ENV`. The Phase 1A production-secret
  guard (`check_production_secrets()`) will refuse to start if any of
  the four secret-bearing values (`ATLAS_SECRET_KEY`, `JWT_SECRET_KEY`,
  `ATLAS_API_KEY`, `POSTGRES_PASSWORD`) are left at their known
  insecure defaults **and** `ATLAS_ENV=production` — this is a real
  safeguard that would need real values set in Render's environment
  variable configuration before a production-mode deploy could succeed.

### 2. A Genuine Configuration Gap Found Through Research (not deployment)

Render's own documentation (render.com/docs/web-services, fetched
directly) states: *"We recommend binding your HTTP server to the port
defined by the `PORT` environment variable"* — Render assigns this
dynamically and forwards inbound traffic to it. **The current Dockerfile
hardcodes `--port 8000`** rather than reading `$PORT`. This is a real,
concrete blocker for an actual Render deployment (not a hypothetical
one) — discovered through documentation research alone, without needing
deployment access to find it. **Not fixed here**, per this phase's
instruction not to modify application logic unless a blocker requires
it and deployment itself never reached the point of confirming this in
practice — flagging it clearly for Phase 2E instead of guessing at a
fix I can't test.

### 3. Provider Verification (official Render documentation, fetched directly)

| Item | Finding | Source |
|---|---|---|
| Free web service cost | $0, described across multiple official pages as requiring no card for the free web-service/static-site/Postgres/Key-Value combination | render.com/docs/free; a Render-published article (render.com/articles/platforms-with-a-real-free-tier-for-developers-in-2026) |
| Card requirement — **conflicting signal found** | Render's own pricing FAQ separately states: *"We accept all major credit and debit cards... A $1 USD transaction is performed as a credit security check... refunded after"* | render.com/pricing — **I could not determine from the fetched text alone whether this $1 check applies to free-tier signup specifically, or only when adding a payment method for a paid plan.** This needs direct confirmation on Render's actual sign-up flow — exactly the kind of thing I should not guess at. |
| Free web service compute | Compute plans were renamed to spec-based IDs in August 2026 (e.g. `1c-2g` = 1 CPU/2GB RAM) for **paid** tiers; the **Free** compute plan is separate and its exact RAM/CPU figure was not stated in the specific pages I retrieved this session (Phase 2B's earlier ~512 MB figure came from secondary sources, still not independently confirmed against Render's current official spec sheet) |
| Sleep/cold-start behavior | **Confirmed, official**: Render spins down a Free web service after **15 minutes with no inbound traffic** (HTTP or WebSocket); spin-up on the next request takes **about one minute**; Render shows visiting browsers a loading page during spin-up | render.com/docs/free |
| Free Postgres storage | **Confirmed, official, and an update to Phase 2B's finding**: fixed **1 GB** storage (Phase 2B had found conflicting secondary-source figures around 256 MB) | render.com/docs/free |
| Free Postgres expiry | **Confirmed, official**: expires **30 days after creation** (Phase 2B's "30 vs 90 days" conflict is now resolved — 30 days is the current official figure) | render.com/docs/free |
| Free Postgres quantity | **Only one Free Postgres database per workspace** | render.com/docs/free |
| Filesystem | Free web services have an **ephemeral filesystem** — any local filesystem changes are lost on redeploy, restart, or spin-down | render.com/docs/free |
| Networking | Free web services **cannot receive private network traffic**, but **can send** private network requests to data stores and paid services in the same region — relevant if the backend and a Render Postgres instance were placed in the same region/workspace | render.com/docs/free |
| Restricted ports | Free web services can't listen on ports 18012/18013/19099, and can't send outbound traffic on SMTP ports 25/465/587 | render.com/docs/free |
| Environment variable support | Supported — set under a service's "Advanced" section during creation, alongside secrets, health-check path, and persistent disks | render.com/docs/web-services |

This resolves and updates two specific open questions Phase 2B flagged
as unresolved (Postgres storage size and expiry duration) with current
official numbers, even though the deployment itself could not be
attempted.

## Cost and Billing Considerations (per your explicit stop conditions)

- **No payment method has been confirmed as required** for the free
  web-service + free Postgres combination, based on the majority of
  sources reviewed — but the conflicting `$1 security-check charge`
  language found on Render's own pricing page means **I cannot state
  with full confidence that no card will ever be requested during
  sign-up.** This is exactly a "provider terms are unclear" situation
  per your stop conditions.
- **No ongoing charges are implied** by anything reviewed, provided the
  Free compute plan is selected and not upgraded.
- Per your explicit instruction, **I am stopping and flagging this for
  your confirmation** rather than proceeding on an assumption: before
  any real sign-up, you (not I) should confirm directly on Render's
  actual sign-up page whether a card is requested, and decide whether
  that's acceptable.

## What Could Not Be Done

Everything under "DEPLOYMENT TEST" in the phase instructions —
deploying the backend, configuring environment variables in a real
Render dashboard, verifying startup/health/DB connectivity/auth against
a live public deployment, and measuring real startup time, first-
request latency, warm-request latency, and sleep/wake behavior on
Render's actual infrastructure — **none of this was performed**, for
the reasons stated above. No numbers are reported for any of these
because none were measured.

## Validation

No code was changed in this phase, so no test re-run was required.
`git status` was checked before and after this phase's work and shows
no unexpected changes — only the documentation file this report adds.

## Did the Backend Pass the Trial?

**Not applicable — no trial occurred.** This is a blocker report, not a
pass/fail result.

## Recommended Phase 2E Next Step

This phase cannot be completed by me alone. The concrete next step is
for **you** to perform the account-level action a human must do:

1. Go to Render's actual sign-up/dashboard yourself and confirm directly
   whether a card is requested for the free web-service + free-Postgres
   flow (resolving the one genuinely unclear item above).
2. If you're comfortable proceeding, connect your GitHub account to
   Render and create the free web service and free Postgres instance
   through Render's own UI.
3. Once that exists, share the resulting public URL (and, separately
   and never as plain chat text, configure the real secret values
   directly in Render's dashboard's environment-variable UI, not
   through me) — at that point I can help verify `/health`, review
   logs you paste in, and interpret real results, since reading and
   reasoning about results you provide doesn't require me to have
   network access to Render myself.
4. Separately, before any real deploy attempt: fix the `$PORT`
   binding gap found in section 2 above — this is a small, well-
   understood change (reading `$PORT` from the environment instead of
   hardcoding 8000) but I'm not making it unprompted in this phase
   since deployment never reached the point of confirming it's the
   *only* blocker, and you may want to review it yourself first.
