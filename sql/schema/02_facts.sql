-- ============================================================
-- Atlas – Fact Tables
-- Schema: warehouse
-- ============================================================
-- Fact tables contain measurable events and business transactions.
-- They are INSERT-only (immutable) — never UPDATE or DELETE.
-- Corrections are handled by inserting a reversing row + new row.
-- All monetary values stored in local currency; GBP conversion
-- is applied in analytics views using dim_country.currency_factor.
-- ============================================================

-- ─── fact_customer_journey ────────────────────────────────────────────────────
-- One row per customer. Tracks milestone dates through the full lifecycle.
-- Drives funnel analytics, time-to-activate, and cohort analysis.
-- Updated (overwrite) by ETL as lifecycle stages are reached.
CREATE TABLE IF NOT EXISTS warehouse.fact_customer_journey (
    journey_id              BIGSERIAL       PRIMARY KEY,
    customer_id             BIGINT          NOT NULL REFERENCES warehouse.dim_customer(customer_id),
    country_id              INTEGER         NOT NULL REFERENCES warehouse.dim_country(country_id),
    channel_id              INTEGER         NOT NULL REFERENCES warehouse.dim_channel(channel_id),
    signup_date_key         INTEGER         NOT NULL REFERENCES warehouse.dim_date(date_key),

    -- Milestone date keys (NULL = stage not yet reached)
    signup_date             DATE            NOT NULL,
    kyc_submission_date     DATE,
    kyc_completion_date     DATE,
    activation_date         DATE,
    first_transaction_date  DATE,
    first_deposit_date      DATE,
    premium_upgrade_date    DATE,
    churn_date              DATE,
    reactivation_date       DATE,

    -- Time-to-milestone metrics (days, computed by ETL)
    days_to_kyc_submission  SMALLINT,       -- signup → kyc submission
    days_to_kyc_completion  SMALLINT,       -- kyc submission → kyc approved/rejected
    days_to_activation      SMALLINT,       -- kyc approved → first transaction
    days_to_premium         INTEGER,        -- activation → premium upgrade

    -- Funnel flags (boolean for fast COUNT aggregations)
    reached_registration    BOOLEAN         NOT NULL DEFAULT TRUE,
    reached_kyc_submitted   BOOLEAN         NOT NULL DEFAULT FALSE,
    reached_kyc_approved    BOOLEAN         NOT NULL DEFAULT FALSE,
    reached_activation      BOOLEAN         NOT NULL DEFAULT FALSE,
    reached_first_deposit   BOOLEAN         NOT NULL DEFAULT FALSE,
    reached_premium         BOOLEAN         NOT NULL DEFAULT FALSE,
    is_churned              BOOLEAN         NOT NULL DEFAULT FALSE,

    -- Acquisition economics
    acquisition_cost_gbp    NUMERIC(8,2),   -- From fact_marketing
    kyc_outcome             VARCHAR(20),    -- 'approved', 'rejected', 'pending'

    created_at              TIMESTAMP       NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP       NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_journey_customer UNIQUE (customer_id)
);

COMMENT ON TABLE warehouse.fact_customer_journey IS 'One row per customer. Core funnel, cohort, and lifecycle analytics table. Drives all Growth and Executive hub KPIs.';

-- ─── fact_transactions ────────────────────────────────────────────────────────
-- The primary monetary fact table. Target scale: 5–10 million rows.
-- Every customer-initiated monetary action is a row here.
CREATE TABLE IF NOT EXISTS warehouse.fact_transactions (
    transaction_id          BIGSERIAL       PRIMARY KEY,
    transaction_uuid        UUID            NOT NULL DEFAULT gen_random_uuid(),
    customer_id             BIGINT          NOT NULL REFERENCES warehouse.dim_customer(customer_id),
    product_id              INTEGER         NOT NULL REFERENCES warehouse.dim_product(product_id),
    country_id              INTEGER         NOT NULL REFERENCES warehouse.dim_country(country_id),
    transaction_date_key    INTEGER         NOT NULL REFERENCES warehouse.dim_date(date_key),

    transaction_date        DATE            NOT NULL,
    transaction_timestamp   TIMESTAMP       NOT NULL,
    transaction_type        VARCHAR(30)     NOT NULL,
    -- 'card_payment','fx_exchange','international_transfer','savings_deposit',
    -- 'savings_withdrawal','investment_buy','investment_sell','subscription_payment'

    -- Monetary (local currency)
    amount_local            NUMERIC(14,2)   NOT NULL,
    currency_code           CHAR(3)         NOT NULL,
    currency_factor         NUMERIC(10,6)   NOT NULL DEFAULT 1.0,
    amount_gbp              NUMERIC(14,2)   NOT NULL,   -- amount_local × currency_factor
    fee_amount_local        NUMERIC(10,2)   NOT NULL DEFAULT 0.00,
    fee_amount_gbp          NUMERIC(10,2)   NOT NULL DEFAULT 0.00,

    -- Transaction metadata
    merchant_name           VARCHAR(150),
    merchant_category       VARCHAR(50),
    status                  VARCHAR(20)     NOT NULL DEFAULT 'completed',
    -- 'completed', 'failed', 'pending', 'reversed'
    failure_reason          VARCHAR(100),

    -- Context (denormalized for query performance)
    customer_segment        VARCHAR(30),    -- Snapshot at time of transaction
    is_premium_customer     BOOLEAN         NOT NULL DEFAULT FALSE,

    created_at              TIMESTAMP       NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE warehouse.fact_transactions IS 'Primary monetary fact table. 5–10M rows target. Drives Revenue, Product, and Customer Intelligence hubs.';

-- ─── fact_product_events ──────────────────────────────────────────────────────
-- Tracks all product interaction events (non-monetary).
-- Drives Product Intelligence Hub: adoption, stickiness, feature usage.
-- Target scale: 10 million+ events.
CREATE TABLE IF NOT EXISTS warehouse.fact_product_events (
    event_id                BIGSERIAL       PRIMARY KEY,
    event_uuid              UUID            NOT NULL DEFAULT gen_random_uuid(),
    customer_id             BIGINT          NOT NULL REFERENCES warehouse.dim_customer(customer_id),
    product_id              INTEGER         NOT NULL REFERENCES warehouse.dim_product(product_id),
    country_id              INTEGER         NOT NULL REFERENCES warehouse.dim_country(country_id),
    event_date_key          INTEGER         NOT NULL REFERENCES warehouse.dim_date(date_key),

    event_date              DATE            NOT NULL,
    event_timestamp         TIMESTAMP       NOT NULL,
    event_type              VARCHAR(50)     NOT NULL,
    -- 'card_activated','savings_opened','savings_closed',
    -- 'investment_opened','investment_closed','transfer_created',
    -- 'premium_viewed','premium_purchased','premium_cancelled',
    -- 'app_login','feature_viewed','onboarding_completed'

    event_properties        JSONB,          -- Flexible event-specific metadata
    device_type             VARCHAR(20),    -- 'iOS', 'Android', 'Web'
    session_id              UUID,

    created_at              TIMESTAMP       NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE warehouse.fact_product_events IS 'Product event log. 10M+ rows. Drives stickiness (DAU/MAU), adoption, and user journey analytics.';

-- ─── fact_revenue ─────────────────────────────────────────────────────────────
-- Aggregated daily revenue per customer per product.
-- Derived from fact_transactions by ETL (pre-aggregated for performance).
-- This is what the Revenue Intelligence Hub queries — not raw transactions.
CREATE TABLE IF NOT EXISTS warehouse.fact_revenue (
    revenue_id              BIGSERIAL       PRIMARY KEY,
    customer_id             BIGINT          NOT NULL REFERENCES warehouse.dim_customer(customer_id),
    product_id              INTEGER         NOT NULL REFERENCES warehouse.dim_product(product_id),
    country_id              INTEGER         NOT NULL REFERENCES warehouse.dim_country(country_id),
    revenue_date_key        INTEGER         NOT NULL REFERENCES warehouse.dim_date(date_key),
    revenue_date            DATE            NOT NULL,

    revenue_type            VARCHAR(30)     NOT NULL,
    -- 'subscription','fx_fee','transfer_fee','investment_fee','card_interchange'

    gross_revenue_local     NUMERIC(12,2)   NOT NULL DEFAULT 0.00,
    gross_revenue_gbp       NUMERIC(12,2)   NOT NULL DEFAULT 0.00,
    refunds_gbp             NUMERIC(12,2)   NOT NULL DEFAULT 0.00,
    net_revenue_gbp         NUMERIC(12,2)   NOT NULL DEFAULT 0.00,   -- gross − refunds

    transaction_count       INTEGER         NOT NULL DEFAULT 0,
    is_premium_revenue      BOOLEAN         NOT NULL DEFAULT FALSE,

    created_at              TIMESTAMP       NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_revenue_grain UNIQUE (customer_id, product_id, revenue_date_key, revenue_type)
);

COMMENT ON TABLE warehouse.fact_revenue IS 'Pre-aggregated daily revenue. Grain: customer × product × date × revenue_type. Query target for Revenue Intelligence Hub.';

-- ─── fact_marketing ───────────────────────────────────────────────────────────
-- Acquisition cost and conversion tracking per customer per channel.
CREATE TABLE IF NOT EXISTS warehouse.fact_marketing (
    marketing_id            BIGSERIAL       PRIMARY KEY,
    customer_id             BIGINT          NOT NULL REFERENCES warehouse.dim_customer(customer_id),
    channel_id              INTEGER         NOT NULL REFERENCES warehouse.dim_channel(channel_id),
    country_id              INTEGER         NOT NULL REFERENCES warehouse.dim_country(country_id),
    touchpoint_date_key     INTEGER         NOT NULL REFERENCES warehouse.dim_date(date_key),

    campaign_id             VARCHAR(50),
    campaign_name           VARCHAR(150),
    touchpoint_date         DATE            NOT NULL,

    acquisition_cost_gbp    NUMERIC(8,2)    NOT NULL DEFAULT 0.00,
    is_converted            BOOLEAN         NOT NULL DEFAULT FALSE,  -- Reached activation
    conversion_date         DATE,
    days_to_conversion      SMALLINT,

    created_at              TIMESTAMP       NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE warehouse.fact_marketing IS 'Acquisition cost and channel conversion. Drives Growth Intelligence Hub CAC calculations.';

-- ─── fact_support ─────────────────────────────────────────────────────────────
-- Customer support ticket resolution performance.
CREATE TABLE IF NOT EXISTS warehouse.fact_support (
    ticket_id               BIGSERIAL       PRIMARY KEY,
    ticket_uuid             UUID            NOT NULL DEFAULT gen_random_uuid(),
    customer_id             BIGINT          NOT NULL REFERENCES warehouse.dim_customer(customer_id),
    country_id              INTEGER         NOT NULL REFERENCES warehouse.dim_country(country_id),
    created_date_key        INTEGER         NOT NULL REFERENCES warehouse.dim_date(date_key),

    created_at              TIMESTAMP       NOT NULL,
    resolved_at             TIMESTAMP,
    first_response_at       TIMESTAMP,

    issue_type              VARCHAR(50)     NOT NULL,
    -- 'kyc_query','transaction_dispute','card_issue','account_access',
    -- 'fee_complaint','product_question','fraud_report','other'
    priority                VARCHAR(10)     NOT NULL DEFAULT 'P2',  -- P1, P2, P3
    status                  VARCHAR(20)     NOT NULL DEFAULT 'open',  -- 'open','in_progress','resolved','closed'
    channel                 VARCHAR(20),    -- 'chat','email','phone','in_app'

    resolution_time_hours   NUMERIC(8,2),   -- Computed: (resolved_at - created_at) in hours
    first_response_time_hrs NUMERIC(8,2),
    satisfaction_score      SMALLINT,       -- CSAT 1–5 (NULL if not rated)
    is_premium_customer     BOOLEAN         NOT NULL DEFAULT FALSE,

    created_date            DATE            NOT NULL
);

COMMENT ON TABLE warehouse.fact_support IS 'Support ticket performance. Drives Operational Intelligence Hub metrics.';

-- ─── fact_kyc_events ──────────────────────────────────────────────────────────
-- One row per KYC submission event. Separate from dim_customer for historical tracking.
CREATE TABLE IF NOT EXISTS warehouse.fact_kyc_events (
    kyc_event_id            BIGSERIAL       PRIMARY KEY,
    customer_id             BIGINT          NOT NULL REFERENCES warehouse.dim_customer(customer_id),
    country_id              INTEGER         NOT NULL REFERENCES warehouse.dim_country(country_id),
    submission_date_key     INTEGER         NOT NULL REFERENCES warehouse.dim_date(date_key),

    submission_date         DATE            NOT NULL,
    submission_timestamp    TIMESTAMP       NOT NULL,
    completion_timestamp    TIMESTAMP,

    kyc_type                VARCHAR(30)     NOT NULL DEFAULT 'standard',  -- 'standard','enhanced'
    outcome                 VARCHAR(20),    -- 'approved','rejected','pending'
    rejection_reason        VARCHAR(100),
    processing_time_hours   NUMERIC(8,2),
    is_resubmission         BOOLEAN         NOT NULL DEFAULT FALSE,
    attempt_number          SMALLINT        NOT NULL DEFAULT 1,

    created_at              TIMESTAMP       NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE warehouse.fact_kyc_events IS 'KYC verification event log. Drives Operational Intelligence Hub KYC analytics.';
