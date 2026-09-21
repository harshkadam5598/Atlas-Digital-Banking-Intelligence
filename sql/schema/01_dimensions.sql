-- ============================================================
-- Atlas – Dimension Tables
-- Schema: warehouse
-- ============================================================
-- Dimensions are the "who, what, when, where" of the star schema.
-- They carry descriptive attributes that fact tables GROUP BY.
-- All dimensions use surrogate integer PKs (not business keys)
-- so that slowly-changing-dimension (SCD) updates don't cascade
-- through fact tables.
-- ============================================================

-- ─── dim_date ─────────────────────────────────────────────────────────────────
-- Pre-populated calendar table covering DATA_START_DATE through +90 days.
-- Eliminates date arithmetic in every KPI query.
-- Populated once by ETL; never updated.
CREATE TABLE IF NOT EXISTS warehouse.dim_date (
    date_key        INTEGER         PRIMARY KEY,          -- YYYYMMDD integer key
    full_date       DATE            NOT NULL UNIQUE,
    day_of_week     SMALLINT        NOT NULL,             -- 1 (Mon) – 7 (Sun)
    day_name        VARCHAR(10)     NOT NULL,             -- 'Monday'
    day_of_month    SMALLINT        NOT NULL,             -- 1–31
    day_of_year     SMALLINT        NOT NULL,             -- 1–366
    week_of_year    SMALLINT        NOT NULL,             -- ISO week 1–53
    month_number    SMALLINT        NOT NULL,             -- 1–12
    month_name      VARCHAR(10)     NOT NULL,             -- 'January'
    month_short     CHAR(3)         NOT NULL,             -- 'Jan'
    quarter         SMALLINT        NOT NULL,             -- 1–4
    quarter_label   VARCHAR(7)         NOT NULL,             -- 'Q1 2024'
    year            SMALLINT        NOT NULL,
    is_weekend      BOOLEAN         NOT NULL DEFAULT FALSE,
    is_month_start  BOOLEAN         NOT NULL DEFAULT FALSE,
    is_month_end    BOOLEAN         NOT NULL DEFAULT FALSE,
    is_quarter_start BOOLEAN        NOT NULL DEFAULT FALSE,
    is_quarter_end  BOOLEAN         NOT NULL DEFAULT FALSE,
    fiscal_year     SMALLINT        NOT NULL,             -- Fiscal year (same as calendar year for Atlas)
    fiscal_quarter  SMALLINT        NOT NULL
);

COMMENT ON TABLE warehouse.dim_date IS 'Pre-populated calendar dimension. One row per day for the full data history range.';

-- ─── dim_country ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS warehouse.dim_country (
    country_id          SERIAL          PRIMARY KEY,
    country_code        CHAR(2)         NOT NULL UNIQUE,  -- ISO 3166-1 alpha-2
    country_name        VARCHAR(100)    NOT NULL,
    region              VARCHAR(50)     NOT NULL,         -- 'Western Europe', 'Americas', etc.
    sub_region          VARCHAR(50),
    currency_code       CHAR(3)         NOT NULL,         -- ISO 4217
    currency_factor     NUMERIC(10,6)   NOT NULL DEFAULT 1.0, -- Rate to GBP (base currency)
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    gdp_per_capita_band VARCHAR(20),                      -- 'High', 'Upper-Middle', 'Lower-Middle', 'Low'
    created_at          TIMESTAMP       NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE warehouse.dim_country IS 'Geographic dimension. Drives market intelligence hub and multi-currency revenue conversion.';
COMMENT ON COLUMN warehouse.dim_country.currency_factor IS 'Multiply local currency amount by this factor to get GBP equivalent.';

-- ─── dim_channel ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS warehouse.dim_channel (
    channel_id          SERIAL          PRIMARY KEY,
    channel_code        VARCHAR(30)     NOT NULL UNIQUE,
    channel_name        VARCHAR(100)    NOT NULL,
    campaign_type       VARCHAR(50)     NOT NULL,         -- 'organic', 'paid_search', 'paid_social', 'referral', 'influencer'
    is_paid             BOOLEAN         NOT NULL DEFAULT FALSE,
    avg_cac_gbp         NUMERIC(8,2),                     -- Benchmark CAC for this channel
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE
);

COMMENT ON TABLE warehouse.dim_channel IS 'Marketing channel dimension. Drives growth intelligence CAC and funnel analytics.';

-- ─── dim_product ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS warehouse.dim_product (
    product_id          SERIAL          PRIMARY KEY,
    product_code        VARCHAR(30)     NOT NULL UNIQUE,
    product_name        VARCHAR(100)    NOT NULL,
    product_category    VARCHAR(50)     NOT NULL,         -- 'card', 'savings', 'investment', 'transfer', 'subscription'
    revenue_model       VARCHAR(50)     NOT NULL,         -- 'transaction_fee', 'subscription', 'spread', 'aum_fee', 'interchange'
    fee_rate            NUMERIC(6,4),                     -- Decimal rate (e.g., 0.005 = 0.5%)
    monthly_fee_gbp     NUMERIC(8,2),                     -- Fixed monthly fee if subscription
    launch_date         DATE            NOT NULL,
    is_premium_only     BOOLEAN         NOT NULL DEFAULT FALSE,
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    description         TEXT
);

COMMENT ON TABLE warehouse.dim_product IS 'Product master. Drives product intelligence hub and revenue attribution.';

-- ─── dim_customer ─────────────────────────────────────────────────────────────
-- SCD Type 1: attributes are overwritten on change (e.g., segment upgrade).
-- For audit-critical SCD Type 2 (e.g., premium status history), use fact_customer_events.
CREATE TABLE IF NOT EXISTS warehouse.dim_customer (
    customer_id             BIGSERIAL       PRIMARY KEY,
    customer_uuid           UUID            NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    signup_date             DATE            NOT NULL,
    signup_date_key         INTEGER         NOT NULL REFERENCES warehouse.dim_date(date_key),
    country_id              INTEGER         NOT NULL REFERENCES warehouse.dim_country(country_id),
    channel_id              INTEGER         NOT NULL REFERENCES warehouse.dim_channel(channel_id),

    -- Demographics
    age_group               VARCHAR(20)     NOT NULL,    -- '18-24', '25-34', '35-44', '45-54', '55+'
    gender                  VARCHAR(20)     NOT NULL,    -- 'Male', 'Female', 'Non-Binary', 'Prefer Not to Say'
    city                    VARCHAR(100),
    occupation              VARCHAR(50),                 -- 'Student', 'Professional', 'Self-Employed', 'Retired', etc.
    income_band             VARCHAR(30),                 -- 'Under 20k', '20k-40k', '40k-70k', '70k-100k', '100k+'

    -- Lifecycle state (SCD Type 1 – reflects current state)
    kyc_status              VARCHAR(20)     NOT NULL DEFAULT 'pending',  -- 'pending', 'approved', 'rejected'
    kyc_submission_date     DATE,
    kyc_completion_date     DATE,
    activation_date         DATE,
    first_transaction_date  DATE,
    premium_upgrade_date    DATE,
    last_activity_date      DATE,
    churn_date              DATE,

    -- Segmentation (recalculated nightly by ETL)
    lifecycle_stage         VARCHAR(30)     NOT NULL DEFAULT 'registered',
    -- 'visitor','registered','kyc_pending','kyc_rejected','activated','churned','reactivated'
    premium_status          BOOLEAN         NOT NULL DEFAULT FALSE,
    customer_segment        VARCHAR(30)     NOT NULL DEFAULT 'registered',
    -- 'power_user','regular_user','occasional_user','dormant','churned'
    clv_band                VARCHAR(20),                 -- 'Platinum','Gold','Silver','Bronze'
    churn_risk_score        NUMERIC(5,2),                -- 0–100 (calculated by analytics engine)
    product_count           SMALLINT        NOT NULL DEFAULT 0,
    total_revenue_gbp       NUMERIC(12,2)   NOT NULL DEFAULT 0.00,

    -- Metadata
    device_type             VARCHAR(20),                 -- 'iOS', 'Android', 'Web'
    is_test_customer        BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at              TIMESTAMP       NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP       NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE warehouse.dim_customer IS 'Customer master dimension (SCD Type 1). Single source of truth for customer identity and current lifecycle state.';
COMMENT ON COLUMN warehouse.dim_customer.churn_risk_score IS 'ML-derived churn probability 0-100. Updated nightly by analytics engine from Sprint 5.';
COMMENT ON COLUMN warehouse.dim_customer.clv_band IS 'CLV quartile band. Recalculated quarterly.';
