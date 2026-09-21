-- ============================================================
-- Atlas – Performance Indexes
-- ============================================================
-- Index strategy:
--   1. All FK columns indexed (join performance)
--   2. Common WHERE predicates covered (date range, status, segment)
--   3. Partial indexes for hot subsets (active customers, completed txns)
--   4. Composite indexes follow selectivity order: high-cardinality first
-- CONCURRENTLY = no table lock; safe to apply on live instances.
-- ============================================================

-- ─── dim_customer ─────────────────────────────────────────────────────────────
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customer_signup_date
    ON warehouse.dim_customer (signup_date);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customer_country
    ON warehouse.dim_customer (country_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customer_channel
    ON warehouse.dim_customer (channel_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customer_lifecycle_stage
    ON warehouse.dim_customer (lifecycle_stage);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customer_segment
    ON warehouse.dim_customer (customer_segment);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customer_premium_status
    ON warehouse.dim_customer (premium_status)
    WHERE premium_status = TRUE;   -- Partial: only premium customers

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customer_kyc_status
    ON warehouse.dim_customer (kyc_status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customer_last_activity
    ON warehouse.dim_customer (last_activity_date DESC);

-- Composite: segment analytics (segment + country + signup month)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customer_segment_country
    ON warehouse.dim_customer (customer_segment, country_id, signup_date);

-- ─── fact_customer_journey ────────────────────────────────────────────────────
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_journey_signup_date_key
    ON warehouse.fact_customer_journey (signup_date_key);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_journey_channel
    ON warehouse.fact_customer_journey (channel_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_journey_country
    ON warehouse.fact_customer_journey (country_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_journey_activation
    ON warehouse.fact_customer_journey (activation_date)
    WHERE activation_date IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_journey_premium_upgrade
    ON warehouse.fact_customer_journey (premium_upgrade_date)
    WHERE premium_upgrade_date IS NOT NULL;

-- Composite: funnel queries (signup date + channel + reached_activation)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_journey_funnel_analysis
    ON warehouse.fact_customer_journey (signup_date_key, channel_id, reached_activation, reached_premium);

-- ─── fact_transactions ────────────────────────────────────────────────────────
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_txn_customer_id
    ON warehouse.fact_transactions (customer_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_txn_date_key
    ON warehouse.fact_transactions (transaction_date_key);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_txn_product_id
    ON warehouse.fact_transactions (product_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_txn_country_id
    ON warehouse.fact_transactions (country_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_txn_status
    ON warehouse.fact_transactions (status);

-- Partial: only completed transactions (majority of analytics queries)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_txn_completed
    ON warehouse.fact_transactions (transaction_date_key, customer_id, amount_gbp)
    WHERE status = 'completed';

-- Partial: failed transactions (operational alerting)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_txn_failed
    ON warehouse.fact_transactions (transaction_date, customer_id)
    WHERE status = 'failed';

-- Composite: revenue aggregation (date + product + country)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_txn_revenue_agg
    ON warehouse.fact_transactions (transaction_date_key, product_id, country_id)
    WHERE status = 'completed';

-- ─── fact_product_events ──────────────────────────────────────────────────────
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pevents_customer
    ON warehouse.fact_product_events (customer_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pevents_date_key
    ON warehouse.fact_product_events (event_date_key);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pevents_product
    ON warehouse.fact_product_events (product_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pevents_event_type
    ON warehouse.fact_product_events (event_type);

-- DAU/MAU stickiness query: date + customer + product
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pevents_stickiness
    ON warehouse.fact_product_events (event_date_key, customer_id, product_id);

-- ─── fact_revenue ─────────────────────────────────────────────────────────────
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_revenue_date_key
    ON warehouse.fact_revenue (revenue_date_key);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_revenue_customer
    ON warehouse.fact_revenue (customer_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_revenue_product
    ON warehouse.fact_revenue (product_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_revenue_country
    ON warehouse.fact_revenue (country_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_revenue_type
    ON warehouse.fact_revenue (revenue_type);

-- Revenue trend aggregation: date + type
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_revenue_trend
    ON warehouse.fact_revenue (revenue_date_key, revenue_type, net_revenue_gbp);

-- ─── fact_marketing ───────────────────────────────────────────────────────────
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_marketing_customer
    ON warehouse.fact_marketing (customer_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_marketing_channel
    ON warehouse.fact_marketing (channel_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_marketing_country
    ON warehouse.fact_marketing (country_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_marketing_converted
    ON warehouse.fact_marketing (is_converted, channel_id, touchpoint_date_key)
    WHERE is_converted = TRUE;

-- ─── fact_support ─────────────────────────────────────────────────────────────
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_support_customer
    ON warehouse.fact_support (customer_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_support_date_key
    ON warehouse.fact_support (created_date_key);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_support_status
    ON warehouse.fact_support (status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_support_issue_type
    ON warehouse.fact_support (issue_type);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_support_open_tickets
    ON warehouse.fact_support (created_date_key, priority)
    WHERE status IN ('open', 'in_progress');

-- ─── fact_kyc_events ──────────────────────────────────────────────────────────
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_kyc_customer
    ON warehouse.fact_kyc_events (customer_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_kyc_date_key
    ON warehouse.fact_kyc_events (submission_date_key);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_kyc_outcome
    ON warehouse.fact_kyc_events (outcome);

-- ─── dim_date ─────────────────────────────────────────────────────────────────
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_date_year_month
    ON warehouse.dim_date (year, month_number);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_date_full_date
    ON warehouse.dim_date (full_date);
