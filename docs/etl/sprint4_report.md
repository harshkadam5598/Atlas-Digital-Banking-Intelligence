> **Note:** This document is superseded by `sprint4_release_audit.md` (the official Sprint 4 release document). Retained for historical reference.

# Atlas Sprint 4 — Implementation Report
**Status: COMPLETE | Date: 2025-01-31**

---

## Executive Summary

Sprint 4 delivered a fully operational, production-grade ETL pipeline that moves data from Sprint 3's synthetic parquet files through three database zones (raw → staging → warehouse) and verifies integrity across 101 automated data quality checks.

**Final pipeline execution result:**

```
Status:            PASSED
DQ Score:          100.0 / 100
Rows Extracted:    81,046
Rows Transformed:  81,046
Rows Loaded:       81,046
Rows Rejected:     0
DQ Checks Passed:  101
DQ Checks Failed:  0
Elapsed:           22.5s
```

---

## Phase 1 Deliverables (Approved)

| Component | Status | Files |
|---|---|---|
| Dataset Versioning | ✅ | `etl/core/versioning.py` |
| ETL Run Context | ✅ | `etl/core/context.py` |
| Extract Layer | ✅ | `etl/extractors/extract.py` |
| Transform Layer | ✅ | `etl/transformers/transform.py` |
| Validation Framework | ✅ | `etl/validators/validate.py` |
| Pipeline Orchestrator | ✅ | `etl/pipeline.py` |

## Phase 2 Deliverables (This Sprint)

| Component | Status | Files |
|---|---|---|
| Load Layer (3-zone) | ✅ | `etl/loaders/load.py` |
| Analytics View Verification | ✅ | `refresh_analytics_views()` in load.py |
| ETL Run Log | ✅ | `pipeline.etl_run_log` populated |
| ETL Execution Report | ✅ | `etl/reports/report.py` |
| Data Lineage Documentation | ✅ | `docs/etl/data_lineage.md` |
| Sprint 4 Audit | ✅ | `docs/etl/sprint4_report.md` |

---

## Engineering Change Log (Phase 2)

### Files Modified

| File | Change | Reason |
|---|---|---|
| `etl/loaders/load.py` | Fixed `_df_to_rows`: NaT → None for all dtype variants | psycopg2 cannot accept `pd.NaT` as TIMESTAMP NULL |
| `etl/loaders/load.py` | Fixed raw zone: use `product_code`/`country_code`, not surrogate IDs | `raw.*` tables store business keys, not warehouse FKs |
| `etl/loaders/load.py` | Fixed `log_etl_run`: pass explicit `total` not `ctx.total_loaded` | `ctx.total_loaded` is set after the log call |
| `etl/transformers/transform.py` | Added NaT→None conversion for `resolved_at`, `created_at`, `submission_timestamp` | Belt-and-suspenders alongside `_df_to_rows` fix |
| `sql/schema/01_dimensions.sql` | `quarter_label CHAR(6)` → `VARCHAR(7)` | "Q1 2024" is 7 characters, not 6 |

### Files Created (Phase 2)

| File | Purpose |
|---|---|
| `docs/etl/data_lineage.md` | Complete 8-dataset lineage chains with SQL traceability |
| `docs/etl/sprint4_report.md` | This document |
| `docs/etl/architecture.md` | ETL architecture decisions (Phase 1, updated Phase 2) |

---

## Load Layer Architecture (Phase 2)

### Three-Zone Design

```
Zone 1: raw.*
  Verbatim source representation. Business keys (product_code, country_code).
  No surrogate IDs. Provides a permanent audit trail of exactly what was ingested.
  Tables: raw.dim_customer_raw, raw.fact_transactions_raw, raw.fact_product_events_raw

Zone 2: staging.*
  Full transformed output: all 30 columns of dim_customer_staged,
  all FK IDs resolved, all date keys computed. No DB FK constraints
  (allows inspection/debugging without FK failures).
  Tables: staging.dim_customer_staged, staging.fact_transactions_staged,
          staging.fact_product_events_staged, staging.fact_revenue_staged

Zone 3: warehouse.*
  Production star schema. FK constraints enforced by PostgreSQL.
  Load order: dim_customer first, then all facts.
  Analytics views verified immediately after load.
```

### Idempotency

Every table uses `TRUNCATE … CASCADE` before `INSERT`. Running the pipeline twice produces identical database state. This is the correct pattern for full synthetic dataset refreshes.

### Transaction Safety

Each zone loads inside a single connection context. Zone 1 and Zone 2 share one connection (they have no FK dependencies between them). Zone 3 loads all warehouse tables sequentially; a single table failure logs an error and continues (does not abort the remaining tables).

---

## Validation Engine (Phase 2 — Final)

**101 checks across 6 categories on the canonical run:**

| Category | Checks | All Pass |
|---|---|---|
| Row count reconciliation | 8 | ✅ |
| Referential integrity (in-memory + DB) | 26 | ✅ |
| Business rules (BR-001 through BR-013) | 17 | ✅ |
| Constraint validation (UNIQUE, date range, FK NOT NULL) | 22 | ✅ |
| Fraud / risk event integrity | 6 | ✅ |
| Database row count verification | 8 | ✅ |
| Distribution checks | 14 | ✅ |
| **Total** | **101** | **✅ 100/100** |

---

## Analytics Views Verification

All 10 analytics views populated correctly after the canonical run:

| View | Rows (sample) |
|---|---|
| `v_monthly_business_summary` | 36 |
| `v_mau_trend` | 38 |
| `v_acquisition_funnel` | 265 |
| `v_cohort_retention` | 600 |
| `v_product_adoption` | 343 |
| `v_revenue_by_geography` | 2,411 |
| `v_kyc_performance` | 559 |
| `v_support_performance` | 478 |
| `v_customer_value` | 6 |
| `v_cac_by_channel` | 265 |

---

## Architecture Decision Records (Phase 2 Additions)

**AD-06: NaT conversion in `_df_to_rows`, not in the transform layer**
The root fix for `pd.NaT` → SQL `NULL` conversion belongs in `_df_to_rows` (the boundary between Python and psycopg2). Belt-and-suspenders conversions were also added in the transform layer, but the canonical fix is in the load layer where the DataFrame-to-DB boundary is crossed. This prevents the class of bug from recurring for any future table added to the pipeline.

**AD-07: Raw zone stores business keys, not surrogate IDs**
`raw.fact_transactions_raw` stores `product_code` and `country_code`, not `product_id` and `country_id`. The raw zone's purpose is to be an immutable record of what arrived from the source system. Surrogate ID resolution is a warehouse concern, not a raw concern.

**AD-08: Analytics views verified but not refreshed**
Analytics views in this database are SQL views (not materialised views). They are verified by `SELECT COUNT(*)` after each warehouse load. In Sprint 5, if analytics query performance requires materialisation, `REFRESH MATERIALIZED VIEW` will be added to `refresh_analytics_views()`.

---

## Technical Debt Register (Sprint 4 Close)

| ID | Item | Severity | Sprint |
|---|---|---|---|
| TD-01 | `datetime.utcnow()` deprecation in pipeline.py | Low | Sprint 5 |
| TD-02 | Surrogate key maps are static Python dicts (not DB-sourced) | Medium | Sprint 5 integration test |
| TD-03 | No chunked/streaming load for 7M+ transaction rows | Medium | Sprint 5 |
| TD-04 | `raw.fact_support_raw` and `raw.fact_kyc_events_raw` always 0 rows (not wired to _load_raw_zone) | Low | Sprint 5 |
| TD-05 | `pipeline.data_quality_checks` table not populated per-check (only run-level summary) | Low | Sprint 5 |

TD-04 note: the support and kyc raw zone tables exist in the DB but `_load_raw_zone` currently only loads dim_customer, transactions, and product_events into the raw zone. Support and KYC raw tables are defined but not populated. This does not affect warehouse or analytics correctness.

---

## Performance Summary

| Stage | Duration | Rows/sec |
|---|---|---|
| Extract | 0.50s | 162,092 |
| Transform | 1.01s | 80,243 |
| Load (all 3 zones) | 20.57s | 3,940 |
| Validate | 0.09s | — |
| **Total** | **22.5s** | — |

Load throughput of 3,940 rows/sec is driven by `psycopg2.extras.execute_batch` with `page_size=5000`. At full 500K customer scale (~81M total rows across all tables), expected load time is ~5.7 hours. Chunked loading (TD-03) would reduce this to ~45 minutes using parallel table loads.
