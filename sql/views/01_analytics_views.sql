-- ============================================================
-- Atlas – Analytics Layer Views
-- Schema: analytics
-- ============================================================
-- These views are the ONLY thing the API layer queries.
-- All business logic (currency conversion, segment labelling,
-- KPI calculations) lives here — not in Python API handlers.
-- Views are replaced in full on each ETL run.
-- ============================================================

-- ─── Executive: Monthly Business Summary ─────────────────────────────────────
CREATE OR REPLACE VIEW analytics.v_monthly_business_summary AS
SELECT
    d.year,
    d.month_number,
    d.month_name,
    d.quarter,
    DATE_TRUNC('month', r.revenue_date)::DATE            AS month_start,

    -- Revenue
    SUM(r.net_revenue_gbp)                               AS total_net_revenue_gbp,
    SUM(r.gross_revenue_gbp)                             AS total_gross_revenue_gbp,
    SUM(CASE WHEN r.revenue_type = 'subscription'
             THEN r.net_revenue_gbp ELSE 0 END)          AS subscription_revenue_gbp,
    SUM(CASE WHEN r.revenue_type = 'fx_fee'
             THEN r.net_revenue_gbp ELSE 0 END)          AS fx_revenue_gbp,
    SUM(CASE WHEN r.revenue_type = 'transfer_fee'
             THEN r.net_revenue_gbp ELSE 0 END)          AS transfer_revenue_gbp,
    SUM(CASE WHEN r.revenue_type = 'investment_fee'
             THEN r.net_revenue_gbp ELSE 0 END)          AS investment_revenue_gbp,
    SUM(CASE WHEN r.revenue_type = 'card_interchange'
             THEN r.net_revenue_gbp ELSE 0 END)          AS card_revenue_gbp,

    -- Customer counts (from customer dimension snapshot)
    COUNT(DISTINCT r.customer_id)                        AS paying_customers,
    SUM(r.transaction_count)                             AS total_transactions

FROM warehouse.fact_revenue r
JOIN warehouse.dim_date d ON d.date_key = r.revenue_date_key
GROUP BY d.year, d.month_number, d.month_name, d.quarter, DATE_TRUNC('month', r.revenue_date)
ORDER BY d.year, d.month_number;

COMMENT ON VIEW analytics.v_monthly_business_summary IS 'Month-level revenue aggregation. Executive Command Center primary data source.';

-- ─── Executive: Active Customer Counts ───────────────────────────────────────
CREATE OR REPLACE VIEW analytics.v_mau_trend AS
SELECT
    DATE_TRUNC('month', c.last_activity_date)::DATE      AS activity_month,
    COUNT(DISTINCT c.customer_id)                         AS mau,
    COUNT(DISTINCT CASE WHEN c.premium_status
                   THEN c.customer_id END)                AS premium_mau,
    COUNT(DISTINCT CASE WHEN NOT c.premium_status
                        AND c.lifecycle_stage = 'activated'
                   THEN c.customer_id END)                AS free_mau
FROM warehouse.dim_customer c
WHERE c.lifecycle_stage NOT IN ('registered', 'kyc_pending', 'kyc_rejected')
  AND c.is_test_customer = FALSE
  AND c.last_activity_date IS NOT NULL
GROUP BY DATE_TRUNC('month', c.last_activity_date)
ORDER BY activity_month;

COMMENT ON VIEW analytics.v_mau_trend IS 'Monthly Active User trend. Drives MAU KPI and growth charts.';

-- ─── Growth: Full Acquisition Funnel ─────────────────────────────────────────
CREATE OR REPLACE VIEW analytics.v_acquisition_funnel AS
SELECT
    d.year,
    d.month_number,
    d.month_name,
    DATE_TRUNC('month', j.signup_date)::DATE             AS cohort_month,
    ch.channel_name,
    ch.campaign_type,

    COUNT(*)                                             AS total_registrations,
    SUM(CASE WHEN j.reached_kyc_submitted  THEN 1 ELSE 0 END) AS kyc_submitted,
    SUM(CASE WHEN j.reached_kyc_approved   THEN 1 ELSE 0 END) AS kyc_approved,
    SUM(CASE WHEN j.reached_activation     THEN 1 ELSE 0 END) AS activated,
    SUM(CASE WHEN j.reached_first_deposit  THEN 1 ELSE 0 END) AS first_deposit,
    SUM(CASE WHEN j.reached_premium        THEN 1 ELSE 0 END) AS premium_upgrades,

    -- Conversion rates at each funnel stage
    ROUND(100.0 * SUM(CASE WHEN j.reached_kyc_submitted THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0), 2)                        AS reg_to_kyc_pct,
    ROUND(100.0 * SUM(CASE WHEN j.reached_kyc_approved THEN 1 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN j.reached_kyc_submitted THEN 1 ELSE 0 END), 0), 2) AS kyc_approval_pct,
    ROUND(100.0 * SUM(CASE WHEN j.reached_activation THEN 1 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN j.reached_kyc_approved THEN 1 ELSE 0 END), 0), 2)  AS kyc_to_activation_pct,
    ROUND(100.0 * SUM(CASE WHEN j.reached_premium THEN 1 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN j.reached_activation THEN 1 ELSE 0 END), 0), 2)    AS free_to_premium_pct,

    -- End-to-end conversion
    ROUND(100.0 * SUM(CASE WHEN j.reached_activation THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0), 2)                        AS overall_conversion_pct,

    -- Time-to-activate
    ROUND(AVG(j.days_to_activation), 1)                  AS avg_days_to_activate,
    PERCENTILE_CONT(0.5) WITHIN GROUP
        (ORDER BY j.days_to_activation)                  AS median_days_to_activate

FROM warehouse.fact_customer_journey j
JOIN warehouse.dim_date d   ON d.date_key = j.signup_date_key
JOIN warehouse.dim_channel ch ON ch.channel_id = j.channel_id
GROUP BY d.year, d.month_number, d.month_name,
         DATE_TRUNC('month', j.signup_date), ch.channel_name, ch.campaign_type
ORDER BY cohort_month, ch.channel_name;

COMMENT ON VIEW analytics.v_acquisition_funnel IS 'Full acquisition funnel by month and channel. Growth Intelligence Hub primary source.';

-- ─── Customer: Cohort Retention Matrix ───────────────────────────────────────
CREATE OR REPLACE VIEW analytics.v_cohort_retention AS
WITH cohort_base AS (
    SELECT
        customer_id,
        DATE_TRUNC('month', signup_date)::DATE AS cohort_month,
        activation_date
    FROM warehouse.fact_customer_journey
    WHERE reached_activation = TRUE
),
cohort_activity AS (
    SELECT
        cb.cohort_month,
        cb.customer_id,
        DATE_TRUNC('month', ft.transaction_date)::DATE AS activity_month,
        EXTRACT(YEAR FROM AGE(
            DATE_TRUNC('month', ft.transaction_date),
            cb.cohort_month
        )) * 12 +
        EXTRACT(MONTH FROM AGE(
            DATE_TRUNC('month', ft.transaction_date),
            cb.cohort_month
        ))                                              AS period_number
    FROM cohort_base cb
    JOIN warehouse.fact_transactions ft ON ft.customer_id = cb.customer_id
    WHERE ft.status = 'completed'
      AND ft.transaction_date >= cb.activation_date
)
SELECT
    ca.cohort_month,
    ca.period_number,
    COUNT(DISTINCT cb.customer_id)                      AS cohort_size,
    COUNT(DISTINCT ca.customer_id)                      AS retained_customers,
    ROUND(100.0 * COUNT(DISTINCT ca.customer_id)
        / NULLIF(COUNT(DISTINCT cb.customer_id), 0), 2) AS retention_rate_pct
FROM cohort_activity ca
JOIN cohort_base cb ON cb.cohort_month = ca.cohort_month
WHERE ca.period_number BETWEEN 0 AND 24
GROUP BY ca.cohort_month, ca.period_number
ORDER BY ca.cohort_month, ca.period_number;

COMMENT ON VIEW analytics.v_cohort_retention IS 'Cohort retention matrix. Rows=cohort months, cols=period offsets 0-24. Customer Intelligence Hub.';

-- ─── Product: Adoption and Stickiness ────────────────────────────────────────
CREATE OR REPLACE VIEW analytics.v_product_adoption AS
SELECT
    p.product_name,
    p.product_category,
    d.year,
    d.month_number,
    DATE_TRUNC('month', pe.event_date)::DATE            AS month_start,

    COUNT(DISTINCT pe.customer_id)                      AS monthly_active_users,
    COUNT(DISTINCT CASE WHEN d.full_date = CURRENT_DATE - INTERVAL '1 day'
                        THEN pe.customer_id END)        AS daily_active_users_yesterday,
    COUNT(pe.event_id)                                  AS total_events,

    -- Stickiness proxy (DAU yesterday / MAU this month)
    ROUND(
        COUNT(DISTINCT CASE WHEN d.full_date = CURRENT_DATE - INTERVAL '1 day'
                            THEN pe.customer_id END)::NUMERIC
        / NULLIF(COUNT(DISTINCT pe.customer_id), 0), 3
    )                                                   AS stickiness_ratio

FROM warehouse.fact_product_events pe
JOIN warehouse.dim_product p  ON p.product_id = pe.product_id
JOIN warehouse.dim_date d     ON d.date_key = pe.event_date_key
GROUP BY p.product_name, p.product_category, d.year, d.month_number,
         DATE_TRUNC('month', pe.event_date)
ORDER BY month_start DESC, monthly_active_users DESC;

COMMENT ON VIEW analytics.v_product_adoption IS 'Product adoption and stickiness by month. Product Intelligence Hub.';

-- ─── Revenue: By Type and Country ────────────────────────────────────────────
CREATE OR REPLACE VIEW analytics.v_revenue_by_geography AS
SELECT
    co.region,
    co.country_name,
    co.country_code,
    d.year,
    d.month_number,
    DATE_TRUNC('month', r.revenue_date)::DATE           AS month_start,
    r.revenue_type,

    COUNT(DISTINCT r.customer_id)                       AS paying_customers,
    SUM(r.net_revenue_gbp)                              AS net_revenue_gbp,
    ROUND(SUM(r.net_revenue_gbp)
        / NULLIF(COUNT(DISTINCT r.customer_id), 0), 2) AS arpu_gbp

FROM warehouse.fact_revenue r
JOIN warehouse.dim_country co ON co.country_id = r.country_id
JOIN warehouse.dim_date d     ON d.date_key = r.revenue_date_key
GROUP BY co.region, co.country_name, co.country_code,
         d.year, d.month_number, DATE_TRUNC('month', r.revenue_date), r.revenue_type
ORDER BY month_start DESC, net_revenue_gbp DESC;

COMMENT ON VIEW analytics.v_revenue_by_geography IS 'Revenue by country and region. Market Intelligence Hub primary source.';

-- ─── Operational: KYC Performance ────────────────────────────────────────────
CREATE OR REPLACE VIEW analytics.v_kyc_performance AS
SELECT
    DATE_TRUNC('month', k.submission_date)::DATE        AS month_start,
    co.region,
    co.country_name,
    k.kyc_type,

    COUNT(*)                                            AS total_submissions,
    SUM(CASE WHEN k.outcome = 'approved' THEN 1 ELSE 0 END) AS approved,
    SUM(CASE WHEN k.outcome = 'rejected' THEN 1 ELSE 0 END) AS rejected,
    SUM(CASE WHEN k.outcome = 'pending'  THEN 1 ELSE 0 END) AS pending,
    SUM(CASE WHEN k.is_resubmission      THEN 1 ELSE 0 END) AS resubmissions,

    ROUND(100.0 * SUM(CASE WHEN k.outcome = 'approved' THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0), 2)                       AS approval_rate_pct,
    ROUND(AVG(k.processing_time_hours), 1)              AS avg_processing_hours,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP
        (ORDER BY k.processing_time_hours)::NUMERIC, 1) AS median_processing_hours

FROM warehouse.fact_kyc_events k
JOIN warehouse.dim_country co ON co.country_id = k.country_id
GROUP BY DATE_TRUNC('month', k.submission_date), co.region, co.country_name, k.kyc_type
ORDER BY month_start DESC, total_submissions DESC;

COMMENT ON VIEW analytics.v_kyc_performance IS 'KYC processing performance by month and country. Operational Intelligence Hub.';

-- ─── Operational: Support Performance ────────────────────────────────────────
CREATE OR REPLACE VIEW analytics.v_support_performance AS
SELECT
    DATE_TRUNC('month', s.created_date)::DATE           AS month_start,
    s.issue_type,
    s.priority,

    COUNT(*)                                            AS total_tickets,
    SUM(CASE WHEN s.status = 'resolved' THEN 1 ELSE 0 END) AS resolved_tickets,
    ROUND(100.0 * SUM(CASE WHEN s.status = 'resolved' THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0), 2)                       AS resolution_rate_pct,

    ROUND(AVG(s.resolution_time_hours), 1)              AS avg_resolution_hours,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP
        (ORDER BY s.resolution_time_hours)::NUMERIC, 1) AS median_resolution_hours,
    ROUND(AVG(s.first_response_time_hrs), 1)            AS avg_first_response_hours,
    ROUND(AVG(s.satisfaction_score::NUMERIC), 2)        AS avg_csat_score,
    SUM(CASE WHEN s.is_premium_customer THEN 1 ELSE 0 END) AS premium_tickets

FROM warehouse.fact_support s
GROUP BY DATE_TRUNC('month', s.created_date), s.issue_type, s.priority
ORDER BY month_start DESC, total_tickets DESC;

COMMENT ON VIEW analytics.v_support_performance IS 'Support ticket performance by month, type, and priority. Operational Intelligence Hub.';

-- ─── Customer: ARPU and CLV Bands ────────────────────────────────────────────
CREATE OR REPLACE VIEW analytics.v_customer_value AS
SELECT
    c.clv_band,
    c.customer_segment,
    c.lifecycle_stage,
    co.region,

    COUNT(c.customer_id)                                AS customer_count,
    ROUND(AVG(c.total_revenue_gbp), 2)                  AS avg_revenue_gbp,
    ROUND(SUM(c.total_revenue_gbp), 2)                  AS total_revenue_gbp,
    ROUND(100.0 * COUNT(c.customer_id)
        / SUM(COUNT(c.customer_id)) OVER (), 2)         AS pct_of_customers,
    ROUND(100.0 * SUM(c.total_revenue_gbp)
        / SUM(SUM(c.total_revenue_gbp)) OVER (), 2)     AS pct_of_revenue,
    COUNT(CASE WHEN c.premium_status THEN 1 END)        AS premium_count,
    ROUND(100.0 * COUNT(CASE WHEN c.premium_status THEN 1 END)
        / NULLIF(COUNT(c.customer_id), 0), 2)           AS premium_pct

FROM warehouse.dim_customer c
JOIN warehouse.dim_country co ON co.country_id = c.country_id
WHERE c.lifecycle_stage = 'activated'
  AND c.is_test_customer = FALSE
GROUP BY c.clv_band, c.customer_segment, c.lifecycle_stage, co.region
ORDER BY avg_revenue_gbp DESC;

COMMENT ON VIEW analytics.v_customer_value IS 'Customer value distribution by CLV band and segment. Customer Intelligence Hub.';

-- ─── Growth: CAC by Channel ───────────────────────────────────────────────────
CREATE OR REPLACE VIEW analytics.v_cac_by_channel AS
SELECT
    DATE_TRUNC('month', m.touchpoint_date)::DATE        AS month_start,
    ch.channel_name,
    ch.campaign_type,
    ch.is_paid,

    COUNT(DISTINCT m.customer_id)                       AS total_leads,
    COUNT(DISTINCT CASE WHEN m.is_converted THEN m.customer_id END) AS conversions,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN m.is_converted THEN m.customer_id END)
        / NULLIF(COUNT(DISTINCT m.customer_id), 0), 2)  AS conversion_rate_pct,

    SUM(m.acquisition_cost_gbp)                         AS total_spend_gbp,
    ROUND(SUM(m.acquisition_cost_gbp)
        / NULLIF(COUNT(DISTINCT CASE WHEN m.is_converted THEN m.customer_id END), 0), 2) AS cac_gbp,

    ROUND(AVG(m.days_to_conversion), 1)                 AS avg_days_to_convert

FROM warehouse.fact_marketing m
JOIN warehouse.dim_channel ch ON ch.channel_id = m.channel_id
GROUP BY DATE_TRUNC('month', m.touchpoint_date), ch.channel_name, ch.campaign_type, ch.is_paid
ORDER BY month_start DESC, cac_gbp ASC;

COMMENT ON VIEW analytics.v_cac_by_channel IS 'CAC by marketing channel and month. Growth Intelligence Hub.';
