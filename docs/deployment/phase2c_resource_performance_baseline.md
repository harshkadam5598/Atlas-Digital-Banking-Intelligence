# Atlas — Phase 2C: Local Resource & Performance Baseline

Evidence-gathering phase only. No deployment occurred, no cloud accounts
were created, no hosting provider was selected. Every number in this
report was measured through real local execution — none are estimates
or claims carried over from documentation.

## Executive Summary

The sample-scale database (2,000 customers, 81,046 total rows) loaded
successfully end-to-end into a real local PostgreSQL 16 instance with a
**100.0/100 data-quality score** and occupies **68 MB total** — comfortably
within the 0.5 GB free tiers of both Neon and Supabase identified in
Phase 2B, with substantial headroom. The FastAPI backend, running against
this real database, served all six representative endpoints successfully
with real (non-fabricated) response data, peaking at **~228 MB RSS**
(measured via `/proc`'s true high-water mark) under light, single-user,
sequential local testing. This is below the ~512 MB figure reported for
Render's free tier in Phase 2B, but **this was not a load test** — it says
nothing about concurrent-user behavior, and that reported 512 MB figure
was itself never independently confirmed on Render's own site. One
real, pre-existing bug was found and fixed along the way (see
"Errors and Blockers").

## Environment and Versions

| Component | Version | Note |
|---|---|---|
| PostgreSQL | 16.15 (Ubuntu build) | Installed natively in this sandbox (no Docker available — same constraint as Phase 1B) |
| Python | 3.12.3 | Repository pins target 3.11 in the Dockerfile; not re-tested against 3.11 here |
| FastAPI | 0.111.0 | |
| Uvicorn | 0.29.0 | |
| pandas | 2.2.2 | |
| numpy | 1.26.4 | |
| scikit-learn | 1.4.2 | |
| statsmodels | 0.14.2 | |
| SQLAlchemy | 2.0.30 | |
| psycopg2-binary | 2.9.9 | |
| Sandbox host | 1 vCPU, 3.9 GB RAM total | **Not representative of any target hosting provider** — used only to obtain Atlas's own absolute resource footprint, not to simulate a specific host's constraints |

## Errors and Blockers

### Blocker 1: missing `tqdm` dependency (fixed)
The documented sample-generation command
(`python -m etl.extractors.pipeline_orchestrator --sample 2000`) failed
immediately with `ModuleNotFoundError: No module named 'tqdm'`.
`etl/extractors/pipeline_orchestrator.py` imports `tqdm` directly, but
it was declared in neither `requirements.txt` nor `requirements-dev.txt`
— confirmed by grepping both files. **Fix applied**: added
`tqdm==4.70.1` to `requirements.txt`'s "ETL & Data Pipeline" section
(the version that actually installed and worked). This is additive
only — no existing pinned version was changed, no import behavior was
altered, and the full offline test suite (208 tests) was re-run
afterward with no regressions (see Validation).

### Blocker 2: stale tracked checkpoint files (worked around, not modified)
`data/raw/.checkpoints/stage_0{1-6}.json` are tracked in git from the
original Sprint 6 release, but their corresponding `.parquet` outputs
were never committed (by design — `data/raw/*.parquet` is gitignored).
This made the pipeline believe generation was already complete and try
to load nonexistent files. The script already provides the correct
mechanism for this (`--force`, per its own usage docstring), which was
used instead of touching any tracked file. Running with `--force`
regenerated the checkpoint files and validation/reproducibility JSON
with this run's real output — these now show as modified in `git
status` as a direct, expected consequence of following the documented
process, not a separate change.

Neither of these affects application business logic, analytics
calculations, or API contracts.

## Database-Size Measurements

**Two distinct states were tested, exactly as required:**

### Schema-only (structure, no transactional data)
Carried over from Phase 1B's verified state: schema + 67 indexes + 10
analytics views + `dim_date` (1,811 rows), zero rows in every fact
table. Not re-measured for size in this phase (Phase 1B already
established this state works); this phase's new work started from
there and loaded real data on top.

### Data-loaded (sample-scale, 2,000 customers)

Loaded via the exact documented, reproducible commands:
```bash
DATA_CUSTOMER_COUNT=2000 python -m etl.extractors.pipeline_orchestrator --sample 2000 --force
POSTGRES_HOST=localhost POSTGRES_PORT=5432 POSTGRES_DB=atlas_db \
POSTGRES_USER=atlas_user POSTGRES_PASSWORD=atlas_password python -m etl.pipeline
```
Extraction: 81,046 rows generated in ~4s. Load: 81,046 rows loaded in
~17s, **DQ Score 100.0/100, 101/101 database checks passed**, all six
fact-table row counts matched their expected values exactly (Δ=+0 on
every table). The total row count (81,046) exactly matches the figure
documented in the original Sprint 6 README's canonical run — confirming
reproducibility with the same seed (42).

**Total database size: 68 MB**
(`SELECT pg_size_pretty(pg_database_size('atlas_db'))`)

### Table and Index Sizes

| Table | Total size | Table only | Indexes+TOAST | Row count |
|---|---|---|---|---|
| `warehouse.fact_product_events` | 19 MB | 15 MB | 3,752 kB | 34,705 |
| `warehouse.fact_transactions` | 6,184 kB | 3,176 kB | 3,008 kB | 19,399 |
| `warehouse.fact_revenue` | 5,568 kB | 2,000 kB | 3,568 kB | 17,772 |
| `warehouse.dim_customer` | 1,040 kB | 384 kB | 656 kB | 2,000 |
| `warehouse.fact_customer_journey` | 680 kB | 256 kB | 424 kB | 2,000 |
| `warehouse.fact_kyc_events` | 504 kB | 248 kB | 256 kB | 2,093 |
| `warehouse.fact_marketing` | 480 kB | 184 kB | 296 kB | 2,000 |
| `warehouse.dim_date` | 400 kB | 168 kB | 232 kB | 1,811 |
| `warehouse.fact_support` | 360 kB | 160 kB | 200 kB | 1,077 |
| `warehouse.dim_product` | 48 kB | 8 kB | 40 kB | 10 |
| `warehouse.dim_channel` | 40 kB | 8 kB | 32 kB | 8 |
| `warehouse.dim_country` | 40 kB | 8 kB | 32 kB | 22 |

**Total index size across `warehouse`: 12 MB.** Top individual indexes:
`idx_pevents_stickiness` (1,776 kB), `uq_revenue_grain` (1,232 kB),
`idx_revenue_trend` (1,016 kB), `idx_txn_completed` (912 kB).

Spot-checked two analytics views directly against the loaded data —
both returned real, correctly-computed business figures (e.g.
`v_monthly_business_summary` for Dec 2024: £1,398.43 total net revenue,
353 paying customers, 654 transactions) — the first time in this
project's history that an analytics view has returned populated data
rather than an empty/structural result.

## Backend Memory Measurements

Method: real `/proc/<pid>/status` readings (`VmRSS` per-stage,
`VmHWM` for true peak) on the actual running `uvicorn` process — not
Python's own `resource` module estimate, which was used only as a
secondary, cruder cross-check.

| Stage | RSS |
|---|---|
| Bare Python interpreter (no imports) | 9.0 MB |
| After `from backend.app.main import create_application; create_application()` (import-only, no server) | 177.5 MB |
| Running server, immediately after startup (DB-connected, ready to serve) | 186.9 MB |
| After `/health` | 186.9 MB |
| After `/api/v1/executive/kpis` (1st, cold) | 225.3 MB |
| After `/api/v1/executive/kpis` (2nd, warm) | 227.0 MB |
| After `/api/v1/revenue/summary` (1st + 2nd) | 227.0 MB |
| After `/api/v1/customer/segments` (1st + 2nd) | 227.4 MB |
| After `/api/v1/operations/summary` (1st + 2nd) | 227.6 MB |
| After `/api/v1/market/summary` (1st + 2nd) | 227.8 MB |
| **Peak (VmHWM, true high-water mark)** | **228.1 MB** (233,524 kB) |

Observations:
- The single largest jump (~38 MB) happens on the **first** real
  request to `executive/kpis`, consistent with lazy-loaded pandas
  DataFrame construction the first time KPI computation code paths run.
- Memory grows very little after that first request across the
  remaining five endpoints (~2–3 MB total) — no evidence of a leak
  across this short sequence, though this was not a sustained/soak test.
- Native PostgreSQL server itself (separate from the app) used ~81 MB
  RSS summed across its worker processes — irrelevant to a managed
  database host's billing model, included here only for completeness.

## API Performance Measurements

All requests authenticated with `X-API-Key`; all returned real data
(no placeholders, no errors) confirmed by inspecting response bodies.

| Endpoint | Status | Time (1st / cold) | Time (2nd / warm) | Real data? |
|---|---|---|---|---|
| `/health` | 200 | 8 ms | — | Yes — `{"status":"healthy",...,"database":"connected"}` |
| `/api/v1/executive/kpis` | 200 | 182 ms | 95 ms | Yes — real MAU (443), revenue (£1,398.43), `unavailable_fields` correctly populated |
| `/api/v1/revenue/summary` | 200 | 18 ms | 17 ms | Yes — real delta/trend, correct `range_note` |
| `/api/v1/customer/segments` | 200 | 15 ms | 14 ms | Yes — correct `gap_note` present |
| `/api/v1/operations/summary` | 200 | 45 ms | 37 ms | Yes — real KYC/fraud/support/CSAT figures |
| `/api/v1/market/summary` | 200 | 92 ms | 87 ms | Yes — real per-country revenue breakdown, correct `efficiency_note` |

No errors or warnings appeared in the server log across this entire
sequence. All response envelopes matched the `{data, meta, errors}`
shape the frontend was built against.

**Caveat, stated plainly**: these are single-request, sequential, local
timings with no network latency, no concurrent load, and a "warm" cache
in the loose sense of "OS page cache/connection reuse" only —
`cached: false` appears in every response, confirming no
application-level caching is active (consistent with Redis being
unused, per the Phase 1 audit).

## Resource Risk Assessment

| Risk | Assessment |
|---|---|
| **Database storage fit** | **Low risk.** 68 MB against 500 MB (Supabase) / 0.5 GB (Neon) free-tier caps leaves roughly 7x headroom at this sample scale. |
| **Backend memory fit** | **Cannot be confirmed, only weakly supported.** 228 MB peak is below the ~512 MB figure reported for Render's free tier in Phase 2B — but that figure was never independently verified against Render's own current documentation, and this test used exactly one sequential user. Concurrent requests, background tasks, or uvicorn worker-count settings could all push real usage meaningfully higher. |
| **Response latency** | **Low risk at this scale**, all well under a second locally — but this says nothing about added network latency, TLS handshake overhead, or cross-region requests once actually deployed. |
| **Cold-start compounding** (Phase 2A/2B finding) | **Unchanged by this phase** — this was a warm, already-running local server; free-tier sleep/wake behavior was not and cannot be tested locally. |

### What was successfully measured
- Real database size, per-table, per-index, at sample scale, data-loaded
- Real backend memory at each lifecycle stage, including true peak (VmHWM)
- Real response times and correctness for all 6 requested endpoints, cold and warm

### What could not be measured (local-environment limitations)
- Actual behavior on any specific hosting provider's real infrastructure (CPU throttling, network overhead, shared-tenancy effects)
- Concurrent/multi-user load behavior (this test was strictly sequential)
- Cold-start/sleep-wake timing (nothing here was ever put to sleep)
- Long-running memory behavior (possible slow leaks over hours/days of uptime)
- Docker-specific resource behavior (still no Docker daemon available in this sandbox, consistent with every prior phase)

## Deployment Implications

- The sample-scale dataset is now **proven**, not just assumed, to fit comfortably in the free-tier managed Postgres options identified in Phase 2B.
- The backend's real memory footprint (228 MB peak, light load) is **encouraging but not sufficient evidence** to declare Render's free tier (or any specific host) workable — the gap between "fits under light local load" and "fits under real public traffic on that provider's actual infrastructure" remains open.
- No new blockers were found in the request/response path itself — every endpoint tested works correctly end-to-end against real data.

## Recommended Next Step

Before selecting a provider: if feasible, run a short **concurrent load test** (even a simple local tool hitting the running server with 5–10 simultaneous requests) to see whether the ~228 MB peak holds or grows meaningfully under concurrency. Short of that, the most valuable next real-world step is an actual trial deployment of the backend to Render's free tier specifically, to replace the "encouraging but unconfirmed" memory finding with a real answer — since that is the one number from Phase 2B this phase could not independently verify.

## Validation

```
$ python -m pytest tests/analytics/ tests/unit/ -q
........................................................................ [ 34%]
........................................................................ [ 69%]
................................................................         [100%]
208 passed in 10.22s
```
No regressions after the `requirements.txt` change (208 passed — same count as Phase 1A/1B, confirming the `tqdm` addition didn't affect anything else).
