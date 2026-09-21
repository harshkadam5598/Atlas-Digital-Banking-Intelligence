# Atlas – Customer Segment Definitions
*These segments govern how customers are classified in dim_customer.customer_segment, how cohorts are formed in analytics, and how executive dashboards filter and compare populations.*

---

## Primary Segmentation: Lifecycle Stage

| Segment | Definition | Analytics Implication |
|---|---|---|
| **Visitor** | Arrived at platform, not yet registered | Funnel top-of-funnel count only |
| **Registered** | Account created, KYC not yet submitted | Funnel stage 2 |
| **KYC Pending** | KYC submitted, awaiting review | Operational KPI |
| **KYC Rejected** | Failed identity or compliance checks | Excluded from active analytics |
| **Activated** | KYC approved + at least 1 transaction completed | Active customer base |
| **Churned** | No activity for 90+ consecutive days | Churn cohort, excluded from MAU |
| **Reactivated** | Previously churned, returned within 12 months | Resurrection cohort |

---

## Revenue Segmentation: Monetization Tier

| Segment | Criteria | Key Metrics |
|---|---|---|
| **Premium** | Active paid subscription | ARPU target: £25+/month |
| **Free Activated** | Activated, no premium subscription | ARPU target: £3–8/month (transaction fees only) |
| **Free Inactive** | Registered but < 1 transaction in 60 days | At-risk, conversion target |

---

## Behavioural Segmentation: Activity Pattern

| Segment | Definition |
|---|---|
| **Power User** | ≥ 20 transactions/month AND ≥ 3 products active |
| **Regular User** | 5–19 transactions/month |
| **Occasional User** | 1–4 transactions/month |
| **Dormant** | 0 transactions in current month but active in prior 90 days |

---

## Value Segmentation: Customer Lifetime Value Band

| Band | Monthly Revenue Contribution | Top-Line Share |
|---|---|---|
| **Platinum** | Top 5% by CLV | ~25% of revenue |
| **Gold** | Next 15% by CLV | ~35% of revenue |
| **Silver** | Next 30% by CLV | ~25% of revenue |
| **Bronze** | Bottom 50% by CLV | ~15% of revenue |

*CLV banding is recalculated quarterly.*

---

## Acquisition Channel Segments

| Channel | Description | CAC Benchmark |
|---|---|---|
| **Organic Search** | SEO / direct / word of mouth | Lowest CAC |
| **Referral** | Friend referral program | Low-medium CAC, high LTV |
| **Google Ads** | Paid search campaigns | Medium CAC |
| **Social Media** | Paid social (Meta, TikTok) | Medium-high CAC |
| **Influencer** | Creator partnership campaigns | High CAC, variable LTV |

---

## Geographic Segments

| Region | Countries (illustrative) |
|---|---|
| **Western Europe** | UK, Germany, France, Netherlands, Ireland |
| **Eastern Europe** | Poland, Romania, Czech Republic, Hungary |
| **Nordics** | Sweden, Norway, Denmark, Finland |
| **Southern Europe** | Spain, Italy, Portugal, Greece |
| **Americas** | USA, Canada, Brazil |
| **APAC** | Australia, Singapore, Japan |

---

## Cohort Definitions

**Signup Cohort:** Group of customers who registered in the same calendar month. Used for retention and CLV analysis.

**Activation Cohort:** Group of customers who activated (first transaction) in the same calendar month. Used for revenue and product analytics.

**Premium Cohort:** Group of customers who upgraded to Premium in the same calendar month. Used for premium retention analysis.
