-- ============================================================
-- Atlas – Stored Functions and Procedures
-- ============================================================

-- ─── Populate dim_date ────────────────────────────────────────────────────────
-- Generates one row per day between p_start and p_end.
-- Called once at schema init; called again when date range extends.
CREATE OR REPLACE FUNCTION warehouse.populate_dim_date(
    p_start DATE,
    p_end   DATE
) RETURNS INTEGER AS $$
DECLARE
    v_date   DATE := p_start;
    v_count  INTEGER := 0;
BEGIN
    WHILE v_date <= p_end LOOP
        INSERT INTO warehouse.dim_date (
            date_key, full_date, day_of_week, day_name, day_of_month,
            day_of_year, week_of_year, month_number, month_name, month_short,
            quarter, quarter_label, year, is_weekend, is_month_start,
            is_month_end, is_quarter_start, is_quarter_end, fiscal_year, fiscal_quarter
        )
        VALUES (
            TO_CHAR(v_date, 'YYYYMMDD')::INTEGER,
            v_date,
            EXTRACT(ISODOW FROM v_date)::SMALLINT,
            TO_CHAR(v_date, 'Day'),
            EXTRACT(DAY FROM v_date)::SMALLINT,
            EXTRACT(DOY FROM v_date)::SMALLINT,
            EXTRACT(WEEK FROM v_date)::SMALLINT,
            EXTRACT(MONTH FROM v_date)::SMALLINT,
            TO_CHAR(v_date, 'Month'),
            TO_CHAR(v_date, 'Mon'),
            EXTRACT(QUARTER FROM v_date)::SMALLINT,
            'Q' || EXTRACT(QUARTER FROM v_date)::TEXT || ' ' || EXTRACT(YEAR FROM v_date)::TEXT,
            EXTRACT(YEAR FROM v_date)::SMALLINT,
            EXTRACT(ISODOW FROM v_date) IN (6, 7),
            EXTRACT(DAY FROM v_date) = 1,
            v_date = DATE_TRUNC('month', v_date) + INTERVAL '1 month' - INTERVAL '1 day',
            EXTRACT(DAY FROM v_date) = 1 AND EXTRACT(MONTH FROM v_date) IN (1, 4, 7, 10),
            v_date = DATE_TRUNC('quarter', v_date) + INTERVAL '3 months' - INTERVAL '1 day',
            EXTRACT(YEAR FROM v_date)::SMALLINT,
            EXTRACT(QUARTER FROM v_date)::SMALLINT
        )
        ON CONFLICT (date_key) DO NOTHING;

        v_date  := v_date + INTERVAL '1 day';
        v_count := v_count + 1;
    END LOOP;
    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION warehouse.populate_dim_date IS 'Populates dim_date for a date range. Returns row count inserted.';

-- ─── Get or Create dim_date key ───────────────────────────────────────────────
CREATE OR REPLACE FUNCTION warehouse.get_date_key(p_date DATE)
RETURNS INTEGER AS $$
    SELECT TO_CHAR(p_date, 'YYYYMMDD')::INTEGER;
$$ LANGUAGE SQL IMMUTABLE;

-- ─── Update customer lifecycle stage ─────────────────────────────────────────
-- Called by ETL nightly to recalculate lifecycle stage from current data.
CREATE OR REPLACE FUNCTION warehouse.refresh_customer_lifecycle()
RETURNS INTEGER AS $$
DECLARE
    v_updated INTEGER;
BEGIN
    UPDATE warehouse.dim_customer c
    SET
        lifecycle_stage = CASE
            WHEN c.churn_date IS NOT NULL
                 AND c.last_activity_date < CURRENT_DATE - INTERVAL '90 days' THEN 'churned'
            WHEN c.activation_date IS NOT NULL                                  THEN 'activated'
            WHEN c.kyc_status = 'rejected'                                      THEN 'kyc_rejected'
            WHEN c.kyc_submission_date IS NOT NULL
                 AND c.kyc_completion_date IS NULL                              THEN 'kyc_pending'
            ELSE 'registered'
        END,
        updated_at = NOW();

    GET DIAGNOSTICS v_updated = ROW_COUNT;
    RETURN v_updated;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION warehouse.refresh_customer_lifecycle IS 'Recalculates lifecycle_stage for all customers. Run nightly by ETL.';
