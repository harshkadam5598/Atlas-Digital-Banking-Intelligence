# Atlas – Business Rules
*These rules govern synthetic data generation logic, ETL transformations, analytics calculations, and API responses. All rules are derived from the Atlas Master Specification and realistic digital banking operating models.*

---

## BR-001: Customer Lifecycle Sequencing
**Rule:** Customer lifecycle stages are strictly ordered. No stage can be skipped.
```
Visitor → Registered → KYC Submitted → (KYC Approved | KYC Rejected | KYC Pending) → Activated → [Churned | Reactivated]
```
**Implication for data generation:** `activation_date` must always be ≥ `kyc_completion_date` ≥ `signup_date`. Null dates are permitted for stages not yet reached.

---

## BR-002: KYC Outcome Distribution
**Rule:** Synthetic KYC outcomes must follow realistic approval rates.
- KYC Approved: 82%
- KYC Rejected: 8%
- KYC Pending (in-progress): 10%

**Implication:** Only approved customers can have activation dates or transactions.

---

## BR-003: Transaction Validity
**Rule:** A transaction is only valid if:
1. The customer's KYC status is `approved`
2. The transaction date is ≥ the customer's `activation_date`
3. The transaction amount is > 0
4. `fee_amount` ≥ 0 and < `amount`

---

## BR-004: Revenue Attribution
**Rule:** Revenue is attributed to the calendar month of the transaction date, not the settlement date.
**Fee rates by transaction type:**
| Type | Fee Rate |
|---|---|
| FX Exchange | 0.5% of transaction amount |
| International Transfer | 0.4% of transfer amount |
| Card Transaction (interchange) | 1.2% of transaction amount |
| Investment Trade | 0.75% annual AUM (accrued daily) |

---

## BR-005: Premium Subscription Revenue
**Rule:** Premium subscription revenue is recognised monthly.
- Monthly fee: £9.99 (GBP baseline; converted by `dim_country.currency_factor`)
- Only customers with `premium_status = TRUE` generate subscription revenue
- Upgrade date = first day of the month premium was activated
- Downgrade voids subscription revenue from that month forward

---

## BR-006: Churn Definition
**Rule:** A customer is classified as churned when they have had zero transactions AND zero product events for 90 consecutive days.
- Churn date = last_activity_date + 90 days
- Churn flag is updated nightly by the ETL pipeline
- Reactivation: if a churned customer transacts again, their status returns to `Activated` and a reactivation event is logged

---

## BR-007: Cohort Assignment
**Rule:** Cohort assignment is immutable. A customer belongs to the signup cohort of their `signup_date` month/year permanently, even after churn or reactivation.

---

## BR-008: Activation Definition
**Rule:** A customer is `activated` when they have completed their **first successful transaction** (status = `completed`) after KYC approval.
- `fact_customer_journey.activation_date` = date of this first transaction
- Activation Rate window = 30 days post-KYC approval

---

## BR-009: Product Event Integrity
**Rule:** Product events must reference a valid `product_id` from `dim_product`.
- `Card Activated` event can only be fired once per customer per card
- `Premium Purchased` event triggers the `premium_status` flag in `dim_customer`
- `Savings Opened` event is a prerequisite for any savings transaction

---

## BR-010: Date Dimension Completeness
**Rule:** `dim_date` must cover the full data history range: `DATA_START_DATE` through `CURRENT_DATE + 90 days` (to support forecasting).

---

## BR-011: Multi-Currency Handling
**Rule:** All fact table monetary amounts are stored in the customer's local currency. The analytics layer converts to GBP using `dim_country.currency_factor` for cross-country aggregations.
- FX rates are static per country in this version (dynamic rates deferred to Sprint 5+)

---

## BR-012: Data Freshness SLA
**Rule:** The ETL pipeline must complete by 03:00 UTC daily. KPIs displayed in the executive dashboard must reflect data no older than T-1 day (yesterday's close).
- The `etl_run_log` table tracks pipeline start, end, and row counts per run
- Any run exceeding 4 hours triggers an alert

---

## BR-013: Null Handling
**Rule:**
- Dimension foreign keys in fact tables: NEVER NULL (use surrogate key -1 for "Unknown")
- Monetary amounts: NEVER NULL (use 0.00 for zero-fee transactions)
- Date fields for future lifecycle stages (e.g., `premium_upgrade_date` for free customers): NULL is valid

---

## BR-014: Analytics Layer Refresh
**Rule:** Analytics views (`analytics.*` schema) are materialized from warehouse tables nightly.
- Direct queries against `raw.*` or `staging.*` schemas from the API layer are forbidden
- All API endpoints query `analytics.*` or `warehouse.*` only
