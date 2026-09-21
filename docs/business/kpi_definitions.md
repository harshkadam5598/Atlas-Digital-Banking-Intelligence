# Atlas – KPI Definitions
*Single source of truth for all Atlas business metrics. These definitions govern synthetic data generation, analytics engine calculations, and executive dashboard displays. Any deviation must be approved and reflected here first.*

---

## Module 1 — Executive Command Center

### Business Health Score
- **Definition:** Composite weighted score (0–100) reflecting overall platform health across five pillars.
- **Formula:** `(Activation Rate × 0.25) + (30-Day Retention × 0.25) + (Revenue Growth MoM × 0.20) + (NPS Proxy × 0.15) + (Operational Uptime × 0.15)`
- **Target:** ≥ 75 = Healthy | 50–74 = Caution | < 50 = At Risk
- **Cadence:** Daily recalculation, 30-day rolling basis

### Risk Score
- **Definition:** Composite risk exposure score (0–100) across churn risk, revenue concentration, and operational risk.
- **Formula:** `(Churn Risk Weight × 0.35) + (Revenue Concentration × 0.30) + (KYC Rejection Rate × 0.20) + (Failed Transaction Rate × 0.15)`
- **Target:** < 25 = Low | 25–50 = Medium | > 50 = High

### Monthly Active Users (MAU)
- **Definition:** Count of unique customers who completed ≥ 1 transaction or ≥ 1 product event in the calendar month.
- **Formula:** `COUNT(DISTINCT customer_id) WHERE last_activity_date >= DATE_TRUNC('month', CURRENT_DATE)`
- **Excludes:** KYC-pending customers, churned customers

---

## Module 2 — Customer Intelligence

### Customer Lifetime Value (CLV)
- **Definition:** Predicted total revenue a customer will generate over their relationship with the platform.
- **Formula:** `ARPU × Average Lifespan (months) × Gross Margin`
- **Gross Margin assumption:** 65% (digital banking benchmark)
- **Lifespan basis:** Survival analysis on historical cohorts

### Monthly ARPU (Average Revenue Per User)
- **Definition:** Total net revenue in month divided by MAU in that month.
- **Formula:** `SUM(net_revenue) / COUNT(DISTINCT active_customer_id)` per month
- **Includes:** All revenue types (subscription, FX, transfer, investment, card)
- **Excludes:** Refunds, chargebacks

### Churn Rate (Monthly)
- **Definition:** Percentage of customers active in month M−1 who had zero activity in month M.
- **Formula:** `COUNT(churned_in_M) / COUNT(active_in_M-1) × 100`
- **Churned definition:** No transaction AND no product event for 30+ consecutive days

### Cohort Retention Rate
- **Definition:** Percentage of customers from signup cohort (month/quarter) still active N periods later.
- **Formula:** `COUNT(active in period N from cohort C) / COUNT(cohort C at signup) × 100`
- **Periods:** Month 1, 3, 6, 12 post-signup

### Net Promoter Score Proxy (NPS Proxy)
- **Definition:** Estimated NPS derived from satisfaction scores and churn signals (no direct survey data).
- **Formula:** `(% satisfied customers − % at-risk customers) × 100`

---

## Module 3 — Growth Intelligence

### Customer Acquisition Cost (CAC)
- **Definition:** Total marketing spend divided by new paying customers acquired in the period.
- **Formula:** `SUM(acquisition_cost) / COUNT(DISTINCT converted_customer_id)` per channel per month
- **Converted definition:** Customer completed KYC AND made first transaction

### Funnel Conversion Rates
| Stage Transition | Formula |
|---|---|
| Visitor → Registration | `registrations / visitors × 100` |
| Registration → KYC Started | `kyc_started / registrations × 100` |
| KYC Started → KYC Approved | `kyc_approved / kyc_started × 100` |
| KYC Approved → Activated | `activated / kyc_approved × 100` |
| Activated → First Transaction | `first_txn / activated × 100` |
| Free → Premium | `premium_upgrades / eligible_free_users × 100` |

### Time-to-Activate (TTA)
- **Definition:** Median days between registration and first transaction.
- **Formula:** `MEDIAN(first_transaction_date − signup_date)` in days
- **Target:** < 3 days

### Activation Rate
- **Definition:** Percentage of registered customers who completed first transaction within 30 days.
- **Formula:** `COUNT(first_txn within 30d of signup) / COUNT(registrations) × 100`

---

## Module 4 — Product Intelligence

### Product Adoption Rate
- **Definition:** Percentage of active customers who have ever used a given product.
- **Formula:** `COUNT(DISTINCT customer_id with ≥1 event for product P) / COUNT(DISTINCT active_customers) × 100`

### Product Stickiness (DAU/MAU)
- **Definition:** Ratio of daily active product users to monthly active product users.
- **Formula:** `DAU / MAU` per product
- **Benchmark:** > 0.20 = sticky | > 0.50 = highly sticky

### Feature Penetration Rate
- **Definition:** Percentage of eligible customers who have used a specific feature.
- **Formula:** `COUNT(used_feature) / COUNT(eligible_customers) × 100`

### Cross-Sell Rate
- **Definition:** Percentage of customers holding ≥ 2 distinct products.
- **Formula:** `COUNT(customers with product_count ≥ 2) / COUNT(active_customers) × 100`

---

## Module 5 — Revenue Intelligence

### Net Revenue
- **Definition:** Gross revenue minus refunds, chargebacks, and payment processing costs.
- **Components:** Subscription fees + FX margin fees + transfer fees + investment management fees + card interchange fees
- **Excludes:** Customer-to-customer transfers (pass-through)

### Revenue per Product Type
| Product | Revenue Mechanism |
|---|---|
| Premium Subscription | Fixed monthly fee (e.g. £9.99/month) |
| International Transfer | % of transfer amount (e.g. 0.5%) |
| FX Exchange | Spread on mid-market rate (e.g. 0.5%) |
| Investment | Annual management fee (e.g. 0.75% AUM) |
| Card | Interchange fee per transaction (e.g. 1.2%) |

### MoM Revenue Growth
- **Formula:** `(Revenue_M − Revenue_M-1) / Revenue_M-1 × 100`

### Revenue Concentration Risk
- **Definition:** Percentage of total revenue from top 10% of customers.
- **Risk threshold:** > 40% = high concentration risk

---

## Module 6 — Operational Intelligence

### KYC Approval Rate
- **Formula:** `COUNT(kyc_status = 'approved') / COUNT(kyc_submissions) × 100`
- **Target:** ≥ 85%

### KYC Median Processing Time
- **Formula:** `MEDIAN(kyc_completion_date − kyc_submission_date)` in hours
- **Target:** < 24 hours

### Average Resolution Time
- **Formula:** `AVG(resolved_at − created_at)` per ticket type in hours
- **Target:** < 4 hours for P1, < 24 hours for P2

### Failed Transaction Rate
- **Formula:** `COUNT(status = 'failed') / COUNT(ALL transactions) × 100`
- **Alert threshold:** > 2%

---

## Module 7 — Market Intelligence

### Geographic Revenue Contribution
- **Formula:** `SUM(revenue) BY country / SUM(total_revenue) × 100`

### Country Customer Growth Rate MoM
- **Formula:** `(new_customers_M − new_customers_M-1) / new_customers_M-1 × 100` per country
