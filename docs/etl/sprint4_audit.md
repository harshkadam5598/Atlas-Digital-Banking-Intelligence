> **Note:** This document is superseded by `sprint4_release_audit.md` (the official Sprint 4 release document). Retained for historical reference.

# Atlas Sprint 4 — Formal Audit Report
**Audit Date: 2025-01-31 | Auditor: Atlas Engineering**

---

## Sprint 4 Formal Status: PASS WITH WARNINGS

**Rationale:** All four ETL pipeline stages execute without errors. The warehouse is populated with correct row counts, all FK constraints satisfied, all 10 analytics views returning data, and all 101 data quality checks passing. Three warnings are logged on the canonical run — all are known, documented, and non-blocking for Sprint 5.

---

## Architecture Status

| Component | Status | Evidence |
|---|---|---|
| Extract layer | ✅ Operational | 8 tables extracted, schema contracts validated |
| Transform layer | ✅ Operational | 81,046 rows clean, 0 rejected |
| Load layer — raw zone | ✅ Operational | 56,104 raw rows (3 tables populated) |
| Load layer — staging zone | ✅ Operational | 73,876 staging rows (4 tables populated) |
| Load layer — warehouse zone | ✅ Operational | 81,046 warehouse rows (8 tables) |
| Analytics views | ✅ Operational | All 10 views returning non-zero row counts |
| Dataset versioning | ✅ Operational | 5 immutable versions in data/versions/ |
| ETL run log | ✅ Operational | pipeline.etl_run_log populated per run |
| ETL execution report | ✅ Operational | JSON + text report written per run |
| Idempotent re-runs | ✅ Verified | Two consecutive runs produce identical DB state |

---

## Validation Status

### Layer 1 — Schema Integrity
- ✅ All 8 source files present and readable
- ✅ All required columns present in all tables
- ✅ All date columns correctly cast from string to `datetime.date`
- ✅ Zero schema contract violations

### Layer 2 — Business Rule Validation
- ✅ BR-001: Lifecycle date ordering (activation ≥ KYC completion ≥ signup)
- ✅ BR-002: KYC approval rate 82.5% (target 80–84%)
- ✅ BR-002: KYC rejection rate 7.0% (target 6–10%)
- ✅ BR-003: All transaction amounts > 0, all fees ≥ 0
- ✅ BR-004: net_revenue_gbp ≥ 0 on all revenue rows
- ✅ BR-008: Activation only for KYC-approved customers (0 violations)
- ✅ BR-013: Required NOT NULL columns — 0 nulls on all 4 checked columns
- ✅ Premium conversion 20.3% (target 15–25%)
- ✅ GB market share 30.5% (target 24–34%)
- ✅ Failed transaction rate 2.36% (target 1–5%)

### Layer 3 — Referential Integrity
- ✅ 0 orphan customer_ids in all 7 fact tables
- ✅ 0 invalid product_ids in transactions, events, revenue
- ✅ 0 invalid country_ids in all 8 tables
- ✅ 0 invalid channel_ids in customer, journey, marketing
- ✅ All date_keys within valid range (20220101–20241231)
- ✅ 0 null FK columns (country_id, channel_id, product_id, date_keys)

### Layer 4 — Constraint Validation
- ✅ UNIQUE: dim_customer.customer_id — 0 duplicates
- ✅ UNIQUE: dim_customer.customer_uuid — 0 duplicates
- ✅ UNIQUE: fact_customer_journey.customer_id — 0 duplicates
- ✅ UNIQUE: fact_marketing.customer_id — 0 duplicates
- ✅ UNIQUE: fact_revenue grain (customer + product + date + type) — 0 duplicates
- ✅ All date_keys correctly formatted as YYYYMMDD integers

### Layer 5 — Fraud/Risk Event Integrity
- ✅ fraud_flagged present: 183 events
- ✅ fraud_cleared present: 144 events
- ✅ suspicious_transfer present: 1 event
- ✅ chargeback present: 15 events
- ✅ fraud_cleared/flagged ratio 78.7% (target 55–92%)
- ✅ All chargebacks on DEBIT_CARD product only

### Layer 6 — Database Row Count Verification
- ✅ warehouse.dim_customer: 2,000 loaded = 2,000 transformed
- ✅ warehouse.fact_customer_journey: 2,000 = 2,000
- ✅ warehouse.fact_transactions: 19,399 = 19,399
- ✅ warehouse.fact_product_events: 34,705 = 34,705
- ✅ warehouse.fact_revenue: 17,772 = 17,772
- ✅ warehouse.fact_marketing: 2,000 = 2,000
- ✅ warehouse.fact_support: 1,077 = 1,077
- ✅ warehouse.fact_kyc_events: 2,093 = 2,093

**DQ Score: 100.0/100 | 101/101 checks passed**

---

## Remaining Technical Debt

| ID | Item | Sprint Target | Blocking Sprint 5? |
|---|---|---|---|
| TD-01 | `datetime.utcnow()` deprecation | Sprint 5 | No |
| TD-02 | Surrogate key maps are static dicts | Sprint 5 | No |
| TD-03 | No chunked loading for 7M+ rows | Sprint 5 | No |
| TD-04 | support/kyc raw zone not populated | Sprint 5 | No |
| TD-05 | `pipeline.data_quality_checks` not row-level | Sprint 5 | No |

None of the five items of technical debt block Sprint 5. All are logged and will be addressed during analytics engine development.

---

## Warnings on Canonical Run (3)

All three are expected:

1. **"PostgreSQL not reachable — running in dry-run mode"** — appears only on runs where DB is unavailable. Does not appear on the canonical full run (Status: PASSED, not PASS_WITH_WARNINGS).

2. **"DB not available — database count verification skipped"** — same condition.

3. **"Analytics view check or ETL log failed"** — can appear if the second connection (used for view verification and run logging) times out. On the canonical run this did not occur.

The canonical full pipeline run (run_id: `20260628_182557_02bae40c`) has status **PASSED** with zero warnings.

---

## Data Quality Summary

| Metric | Value |
|---|---|
| DQ Score | 100.0 / 100 |
| Checks passed | 101 |
| Checks failed | 0 |
| Rows extracted | 81,046 |
| Rows transformed | 81,046 |
| Rows loaded | 81,046 |
| Rows rejected | 0 |
| Rejection rate | 0.00% |

---

## Readiness for Sprint 5

Sprint 5 (Analytics Engine + KPI Calculations) can begin immediately. All prerequisites are satisfied:

- ✅ PostgreSQL warehouse populated with clean data
- ✅ All 10 analytics views returning correct row counts
- ✅ All FK relationships correct (Sprint 5 queries can join freely)
- ✅ `pipeline.etl_run_log` captures run history
- ✅ ETL is idempotent (Sprint 5 can re-run ETL during development)
- ✅ Dataset versioning allows Sprint 5 to work against specific data snapshots
- ✅ Staging parquets available for analytics engine development without DB dependency

Sprint 5 will implement: KPI calculation engine, churn risk scoring (ML model), CLV band assignment, cohort analytics materialisation, and the Executive Narrative Engine.
