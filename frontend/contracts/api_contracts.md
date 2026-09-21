# Atlas – Frontend API Interface Contracts

## Contract Version: v1
## Base URL: `GET /api/v1/`
## Auth: `X-API-Key` header on every business endpoint

Every request must include a valid `X-API-Key` header matching the
server's configured `ATLAS_API_KEY`. Missing or incorrect keys return
`401 UNAUTHORIZED` in the standard error envelope (see below). This
replaces an earlier Bearer-JWT design — JWT settings remain reserved
in configuration for a future full user-auth build-out, but no
endpoint currently requires or checks a JWT token.

All 8 Intelligence Hubs below are implemented — **36 business
endpoints total**.

---

## Executive Command Center

### `GET /api/v1/executive/kpis`
Query params: `as_of` (optional date)
Top-level KPIs: MAU, MAU growth, revenue, revenue growth, premium
conversion, churn. `activation_rate` and `risk_score` are documented
business metrics with no backing KPI implementation — returned as
`null` with an `unavailable_fields` note rather than fabricated.

### `GET /api/v1/executive/health-score`
Query params: `as_of` (optional date)
Real components (30-day retention, revenue growth MoM) of the
documented Business Health Score formula. `score`/`rating` are `null`
because 3 of the formula's 5 weighted inputs have no backing data
source — see `unavailable_fields`.

### `GET /api/v1/executive/risk-alerts`
No params. Anomalies sorted by severity (critical first), sourced
from the anomaly detection engine.

---

## Revenue Intelligence Hub

### `GET /api/v1/revenue/summary`
Query params: `start_date`, `end_date` (optional dates)
Revenue for the calendar month containing `end_date` (or `start_date`
if omitted), broken down by revenue type. Sprint 5's revenue KPIs are
month-scoped, not arbitrary-range — see `range_note` in the response.

### `GET /api/v1/revenue/trend`
Query params: `granularity` (`day`|`week`|`month`, default `month`)
Revenue time-series. Only `month` has backing analytics — `day`/`week`
return an empty series with an `unavailable_fields` note.

### `GET /api/v1/revenue/forecast`
No params. Revenue forecast via linear trend on the historical monthly
series, with confidence bounds. Uses a 3-month horizon as the closest
equivalent to a "90-day forecast" — see `horizon_note`.

---

## Growth Intelligence Hub

### `GET /api/v1/growth/funnel`
Query params: `as_of` (optional date)
Registration -> KYC Started -> KYC Approved -> Activated -> First
Transaction -> Premium funnel for the registration cohort signing up
in the calendar month containing `as_of`. The Visitor -> Registration
stage is omitted — no visitor/traffic data source exists in the
warehouse; see `metadata.note`.

### `GET /api/v1/growth/cac-by-channel`
Query params: `as_of` (optional date)
Customer acquisition cost per marketing channel for the calendar month
containing `as_of`. See `metadata.converted_definition` for how
"converted" is defined.

### `GET /api/v1/growth/activation-trend`
Query params: `months` (int, default 6, range 1-24), `as_of` (optional date)
Monthly activation-rate time series.

---

## Narrative Intelligence

*(No pre-existing contract section for this hub — added to reflect the
actual implementation.)*

### `GET /api/v1/narrative/briefing`
Query params: `max_insights` (default 5, range 1-20), `max_recommendations` (default 5, range 1-20), `as_of` (optional date)
Executive briefing: top insights by magnitude, top recommendations by
priority, plus risk/opportunity counts.

### `GET /api/v1/narrative/insights`
Query params: `category` (`all`|`risk`|`opportunity`, default `all`), `max_insights` (default 10, range 1-27), `as_of` (optional date)
Plain-English insights explaining KPI movements, filtered by category.

### `GET /api/v1/narrative/risk-summary`
Query params: `as_of` (optional date)
Combined view: risk insights, severity-sorted anomalies, and
risk-category recommendations.

---

## Customer Intelligence Hub

### `GET /api/v1/customer/summary`
Query params: `as_of` (optional date)
Active/new/returning customers, churn rate, retention rate, premium
conversion rate.

### `GET /api/v1/customer/kpis`
Query params: `as_of` (optional date)
All 9 registered customer-domain KPIs.

### `GET /api/v1/customer/kpis/{name}`
Path param: `name` (a customer-domain KPI name). Query params: `as_of` (optional date)
Single-KPI lookup restricted to the customer domain — a name from
another domain returns `404 NOT_FOUND`.

### `GET /api/v1/customer/segments`
Query params: `as_of` (optional date)
No customer-count-by-segment KPI exists in the analytics engine.
Exposes `revenue_by_segment` (net revenue grouped by customer segment)
as the closest existing real capability — see `gap_note`.

### `GET /api/v1/customer/retention`
Query params: `as_of` (optional date), `period_months` (default 1)
Cohort retention rate.

### `GET /api/v1/customer/churn`
Query params: `as_of` (optional date)
Monthly churn rate.

### `GET /api/v1/customer/value`
Query params: `as_of` (optional date)
ARPU, CLV, and LTV/CAC ratio.

---

## Product Intelligence Hub

### `GET /api/v1/product/summary`
Query params: `as_of` (optional date)
Product adoption, stickiness, and cross-sell rate.

### `GET /api/v1/product/kpis`
Query params: `as_of` (optional date)
All 4 registered product-domain KPIs.

### `GET /api/v1/product/kpis/{name}`
Path param: `name` (a product-domain KPI name). Query params: `as_of` (optional date)
Single-KPI lookup restricted to the product domain — a name from
another domain returns `404 NOT_FOUND`.

### `GET /api/v1/product/adoption`
Query params: `as_of` (optional date)
Product adoption rate per product.

### `GET /api/v1/product/stickiness`
Query params: `as_of` (optional date)
Product stickiness (DAU/MAU) per product.

### `GET /api/v1/product/cross-sell`
Query params: `as_of` (optional date)
Cross-sell rate (customers holding 2+ products).

### `GET /api/v1/product/feature-adoption`
Query params: `as_of` (optional date), `feature_event_type` (default `premium_purchased`)
Feature penetration rate for a specific product-event type.

---

## Operations Intelligence Hub

*(No pre-existing contract section for this hub — added to reflect the
actual implementation.)*

### `GET /api/v1/operations/summary`
Query params: `as_of` (optional date)
KYC approval rate, fraud rate, support resolution time, CSAT, failed
transaction rate.

### `GET /api/v1/operations/kpis`
Query params: `as_of` (optional date)
All 6 registered operations-domain KPIs.

### `GET /api/v1/operations/kyc`
Query params: `as_of` (optional date)
KYC approval rate, KYC processing time, and KYC-delay anomalies.

### `GET /api/v1/operations/fraud`
Query params: `as_of` (optional date)
Fraud rate and fraud anomalies.

### `GET /api/v1/operations/support`
Query params: `as_of` (optional date)
Support resolution time and CSAT.

### `GET /api/v1/operations/transactions`
Query params: `as_of` (optional date)
Failed transaction rate and transaction-failure anomalies.

---

## Market Intelligence Hub

*(No pre-existing contract section for this hub — added to reflect the
actual implementation.)*

### `GET /api/v1/market/summary`
Query params: `as_of` (optional date)
Revenue by country, top countries, and LTV/CAC (labeled as an
acquisition-efficiency proxy — see `efficiency_note`).

### `GET /api/v1/market/geographic`
Query params: `as_of` (optional date)
Revenue by country, Geographic Revenue Contribution % (derived), and
Country Customer Growth Rate MoM (derived) — a country dropping to
zero new customers is reported as a defined `-100.0` decline rather
than omitted; a brand-new country with no prior-month base is `null`
(undefined), not fabricated as 0 or infinity.

### `GET /api/v1/market/anomalies`
No params. Country-level revenue anomalies from the anomaly detection
engine.

### `GET /api/v1/market/efficiency`
Query params: `as_of` (optional date)
LTV/CAC ratio, explicitly labeled as an acquisition-efficiency proxy —
Atlas has no formally defined "Market Efficiency" KPI. See
`proxy_note` in the response.

---

## Standard Response Envelope
All responses follow this structure:
```json
{
  "data": { ... },
  "meta": {
    "as_of_date": "YYYY-MM-DD",
    "generated_at": "ISO8601",
    "cached": true,
    "cache_ttl_seconds": 300
  },
  "errors": null
}
```

## Standard Error Response
```json
{
  "data": null,
  "meta": null,
  "errors": [
    { "code": "INVALID_DATE_RANGE", "message": "start_date must be before end_date" }
  ]
}
```

Error codes in use: `INVALID_DATE_RANGE` (400), `INVALID_PARAMETER` (400),
`NOT_FOUND` (404), `UNAUTHORIZED` (401), `DATA_UNAVAILABLE` (503),
`VALIDATION_ERROR` (422, FastAPI's own parameter-type validation),
`INTERNAL_ERROR` (500, unhandled exceptions).
