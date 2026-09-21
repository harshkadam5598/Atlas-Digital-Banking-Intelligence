# Atlas – Database Architecture (Sprint 2)

## Design Philosophy

Atlas uses a **modern analytics engineering approach**: data flows one-directional through four schema zones. The API layer never touches raw or staging schemas. All KPI calculations live in SQL views — not in Python — so logic is single-source and testable with `psql`.

---

## Schema Zones

```
raw.*        → Immutable, as-generated source data (Sprint 3 output)
staging.*    → Cleaned, typed, deduped (ETL Sprint 4 output)
warehouse.*  → Star schema: dim_* + fact_* tables (this sprint)
analytics.*  → Materialized KPI views (queried by API)
pipeline.*   → ETL run logs, data quality audit trail
```

---

## Star Schema Diagram (ER Description)

```
                    ┌──────────────┐
                    │  dim_date    │
                    │  (date_key)  │
                    └──────┬───────┘
                           │ FK: *_date_key
        ┌──────────────────┼──────────────────────┐
        │                  │                       │
        ▼                  ▼                       ▼
┌─────────────┐   ┌──────────────────┐   ┌────────────────────┐
│dim_customer │   │fact_transactions │   │fact_customer_journey│
│(customer_id)│◄──│(customer_id FK)  │   │(customer_id FK)    │
│             │   │(product_id FK)   │   │(channel_id FK)     │
└──────┬──────┘   │(country_id FK)   │   └────────────────────┘
       │          │(date_key FK)     │
       │ FK       └────────┬─────────┘
       ▼                   │ FK                    
┌────────────┐    ┌────────▼────────┐    ┌───────────────────┐
│dim_country │    │  dim_product    │    │   dim_channel     │
│(country_id)│    │  (product_id)   │    │  (channel_id)     │
└────────────┘    └─────────────────┘    └───────────────────┘

Additional fact tables (all join on same 4 dims):
  fact_product_events  → customer_id, product_id, country_id, event_date_key
  fact_revenue         → customer_id, product_id, country_id, revenue_date_key
  fact_marketing       → customer_id, channel_id, country_id, touchpoint_date_key
  fact_support         → customer_id, country_id, created_date_key
  fact_kyc_events      → customer_id, country_id, submission_date_key
```

---

## Table Reference

### Dimensions (5)

| Table | Rows (target) | Purpose |
|---|---|---|
| `dim_date` | ~1,400 (3yr + 90d) | Time intelligence for all facts |
| `dim_country` | 22 | Geographic analytics |
| `dim_channel` | 8 | Acquisition channel analytics |
| `dim_product` | 10 | Product performance |
| `dim_customer` | 500,000 | Customer master (SCD Type 1) |

### Facts (7)

| Table | Rows (target) | Grain |
|---|---|---|
| `fact_customer_journey` | 500,000 | 1 row per customer |
| `fact_transactions` | 5–10M | 1 row per transaction |
| `fact_product_events` | 10M+ | 1 row per product event |
| `fact_revenue` | ~2M | customer × product × date × revenue_type |
| `fact_marketing` | 500,000 | 1 row per customer acquisition touchpoint |
| `fact_support` | ~250,000 | 1 row per support ticket |
| `fact_kyc_events` | ~550,000 | 1 row per KYC submission |

---

## Analytics Views (10)

| View | Drives |
|---|---|
| `v_monthly_business_summary` | Executive Command Center revenue |
| `v_mau_trend` | MAU KPI and growth charts |
| `v_acquisition_funnel` | Growth Hub funnel |
| `v_cohort_retention` | Customer Hub cohort table |
| `v_product_adoption` | Product Hub stickiness |
| `v_revenue_by_geography` | Market Hub |
| `v_kyc_performance` | Operations Hub KYC |
| `v_support_performance` | Operations Hub support |
| `v_customer_value` | Customer Hub CLV bands |
| `v_cac_by_channel` | Growth Hub CAC |

---

## Index Strategy

- **FK indexes:** All foreign key columns indexed (JOIN performance)
- **Partial indexes:** Hot row subsets (completed transactions, premium customers, open tickets) exclude cold rows from index scans
- **Composite indexes:** Ordered by selectivity, matching the most common analytical query patterns
- **CONCURRENTLY:** All indexes created without table locks — safe on live instances

---

## Key Design Decisions

**Why INTEGER date key (YYYYMMDD) not DATE?**
Integer joins are 20–30% faster than DATE joins in PostgreSQL range scans. The `dim_date` lookup on `date_key` avoids date arithmetic in every aggregation query.

**Why pre-aggregate `fact_revenue` from `fact_transactions`?**
At 5–10M transaction rows, SUM(fee_amount) GROUP BY month + product + country is expensive to compute on every API request. `fact_revenue` pre-aggregates to ~2M rows at daily grain, making Revenue Hub API responses sub-100ms without a cache hit.

**Why JSONB in `fact_product_events.event_properties`?**
Product events have heterogeneous schemas (a `transfer_created` event has `amount` and `destination_country`; a `feature_viewed` event has `feature_name` and `screen`). JSONB avoids sparse columns while remaining indexable with `@>` operator.

**Why SCD Type 1 for `dim_customer`?**
Point-in-time customer attribute history (what segment was this customer in March 2023?) is captured via `customer_segment` snapshots in `fact_transactions.customer_segment` (denormalized at insert time). This avoids SCD Type 2 complexity while preserving historical context for the analytics that need it.
