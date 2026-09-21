# Atlas ETL Architecture — Sprint 4

## Overview

The Atlas ETL pipeline is a four-stage, single-pass pipeline that moves data from Sprint 3's synthetic parquet files through to a production-ready PostgreSQL warehouse. All four stages share a single `ETLContext` object that accumulates metrics, audit events, warnings, and errors throughout the run.

```
data/versions/          data/raw/          data/staging/        PostgreSQL
  v001_...                *.parquet           *.parquet          warehouse.*
  v002_...    promote→  .version_pointer  ← transformed   →    analytics.*
  v003_...               
       ↓
   [EXTRACT]  →  [TRANSFORM]  →  [LOAD]  →  [VALIDATE]
       ↓               ↓             ↓            ↓
  ETLContext      ETLContext    ETLContext    ETLContext
  .stages["extract"]  .stages["transform"]  ...
```

---

## Stage 1 — Extract (`etl/extractors/extract.py`)

**Responsibility:** Read parquet files, validate schema compatibility, cast types.

**Input:** `data/raw/*.parquet` (8 files)

**Output:** `Dict[str, pd.DataFrame]` — one DataFrame per table

**Schema contracts** (`SCHEMA_CONTRACTS`) define:
- `required`: columns that must exist (file rejected if missing)
- `date_cols`: columns cast from string to `datetime.date` at extraction
- `nullable`: columns that may contain nulls without rejection

**Metrics logged:**
- Rows per table
- Schema checks passed/failed
- Files missing (warn, not error)
- Total extraction time

---

## Stage 2 — Transform (`etl/transformers/transform.py`)

**Responsibility:** Clean, validate, enrich, and resolve surrogate keys for all 8 tables.

**Input:** Raw DataFrames from Extract

**Output:** `(Dict[str, pd.DataFrame], List[Dict])` — (clean tables, reject log)

**Operations per table (in order):**

| Step | Operation | Detail |
|---|---|---|
| 1 | Type normalisation | int64, float64, date, bool — no object columns in output |
| 2 | NOT NULL enforcement | Required columns; rows with nulls → reject log |
| 3 | Enum validation | kyc_status, lifecycle_stage, txn_status, priority |
| 4 | Business rule checks | BR-001 date ordering, BR-003 amounts, BR-008 activation gate |
| 5 | Deduplication | Unique constraints: customer_id, customer_uuid, revenue grain |
| 6 | FK resolution | country_code → country_id, channel_code → channel_id, etc. |
| 7 | Feature engineering | signup_date_key (YYYYMMDD int), transaction_timestamp, created_at |
| 8 | Null fills | Nullable warehouse columns filled with sentinels (not nulls) |

**Reject log:** Every rejected row carries a `_reject_reason` string. Rejects are written to `data/staging/rejects_<run_id>.parquet`.

**Surrogate key maps** (mirrors `sql/schema/04_seed_data.sql`):
- `COUNTRY_MAP`: 22 entries, code → integer ID
- `CHANNEL_MAP`: 8 entries
- `PRODUCT_MAP`: 10 entries

---

## Stage 3 — Load (`etl/loaders/load.py`) ← Phase 2

**Responsibility:** Bulk-load transformed DataFrames into PostgreSQL.

**Design:** TRUNCATE + INSERT per table in dependency order. Batched at 5,000 rows per `execute_batch` call. Each table loads inside its own transaction cursor — a single table failure does not roll back other tables.

**Idempotency:** TRUNCATE before INSERT makes every run fully idempotent. Running the pipeline twice produces identical database state.

**Load order (FK dependency):**
```
dim_customer (no FKs)
  → fact_customer_journey (FK: customer_id, country_id, channel_id, date_key)
  → fact_transactions     (FK: customer_id, product_id, country_id, date_key)
  → fact_product_events   (FK: customer_id, product_id, country_id, date_key)
  → fact_revenue          (FK: customer_id, product_id, country_id, date_key)
  → fact_marketing        (FK: customer_id, channel_id, country_id, date_key)
  → fact_support          (FK: customer_id, country_id, date_key)
  → fact_kyc_events       (FK: customer_id, country_id, date_key)
```

**Dry-run mode:** `--dry-run` skips load entirely but still runs Extract, Transform, and Validate. Staging parquets are always written.

---

## Stage 4 — Validate (`etl/validators/validate.py`)

**Responsibility:** Post-load verification across 5 check categories.

| Category | Checks | Method |
|---|---|---|
| Row count reconciliation | 8 checks | `transformed rows == loaded rows` |
| Referential integrity | 18 checks | In-memory FK cross-join |
| Business rule validation | 13 checks | BR-002, BR-003, BR-008, BR-013 |
| Constraint validation | 8 checks | UNIQUE, date_key range |
| Fraud event presence | 5 checks | All 4 event types present, cleared/flagged ratio |
| DB count verification | 8 checks | SELECT COUNT(*) vs expected (when DB connected) |

**Total: 70 checks** — DQ Score = (passed / 70) × 100

---

## Dataset Versioning (`etl/core/versioning.py`)

Every generation run creates an immutable directory under `data/versions/`. The ETL always reads from `data/raw/` — a stable path that reflects the most recently promoted version.

```
create_version_dir(seed, label)    → data/versions/v00N_<ts>_seed<N>[_label]/
snapshot_raw_to_version(seed)      → copies raw/ → new version dir
promote_to_raw(vdir)               → copies version files → raw/
list_versions()                    → sorted newest-first with metadata
get_latest_version()               → Path to newest version dir
get_raw_version()                  → version ID reflected in raw/ (from pointer)
```

---

## Run Context (`etl/core/context.py`)

`ETLContext` is the single object threaded through all four stages. It accumulates:
- Per-stage `StageMetrics` (rows_in, rows_out, rejected, duration, warnings, errors)
- Global counters: extracted, transformed, loaded, rejected
- DQ check pass/fail counts (→ DQ Score)
- Audit log: timestamped table-level events
- `build_report()` → dict serialisable to JSON
- `write_report(dir)` → `etl/reports/etl_report_<run_id>.json`

---

## Architecture Decisions

**AD-01: Pandas as the transform engine**
Chosen for Sprint 4 data volumes (2K–500K rows). The transform layer is vectorised — no row-level Python loops outside of generators. At full scale (7M transactions), memory pressure is managed by processing tables sequentially, not holding all 8 DataFrames in memory simultaneously. Sprint 5+ can introduce chunked processing if memory becomes an issue.

**AD-02: TRUNCATE+INSERT over UPSERT**
Synthetic data is regenerated from scratch on each Sprint 3 run. There is no partial update scenario — the entire warehouse is refreshed from a complete new dataset. TRUNCATE+INSERT is 3–5× faster than UPSERT at bulk scale and eliminates partial-state edge cases.

**AD-03: Reject log over abort-on-first-error**
Individual row failures (bad FK, null in required column) go to the reject log rather than aborting the pipeline. This gives the operator visibility into data quality issues without preventing clean rows from being loaded. The DQ score reflects the quality of the incoming data.

**AD-04: Staging parquet always written**
`data/staging/*.parquet` is written after Transform regardless of DB availability. This makes the transform output independently inspectable — analysts can query staging files directly without a database connection. It also serves as the Phase 2 load source for recovery runs.

**AD-05: Surrogate key maps are static Python dicts**
FK resolution (country_code → country_id) uses in-memory dicts that mirror `sql/schema/04_seed_data.sql`. This avoids a DB round-trip during transform and keeps the pipeline DB-independent. The dicts must be kept in sync with seed data — enforced by Sprint 4 Phase 2 integration tests.
