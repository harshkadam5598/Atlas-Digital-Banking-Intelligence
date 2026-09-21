-- ============================================================
-- Atlas – Sprint 2 Database Validation Script
-- Run after applying all schema files to verify correctness.
-- All checks should return 'PASS'.
-- ============================================================

DO $$
DECLARE
    v_count     INTEGER;
    v_fail_count INTEGER := 0;
BEGIN

    -- CHECK 1: All schemas exist
    RAISE NOTICE '--- SCHEMA CHECKS ---';
    FOR v_count IN
        SELECT COUNT(*) FROM information_schema.schemata
        WHERE schema_name IN ('raw','staging','warehouse','analytics','pipeline')
    LOOP
        IF v_count = 5 THEN RAISE NOTICE 'PASS: All 5 schemas exist';
        ELSE RAISE WARNING 'FAIL: Expected 5 schemas, found %', v_count; v_fail_count := v_fail_count + 1;
        END IF;
    END LOOP;

    -- CHECK 2: All dimension tables exist
    RAISE NOTICE '--- DIMENSION TABLE CHECKS ---';
    FOR v_count IN
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_schema = 'warehouse'
          AND table_name IN ('dim_date','dim_country','dim_channel','dim_product','dim_customer')
    LOOP
        IF v_count = 5 THEN RAISE NOTICE 'PASS: All 5 dimension tables exist';
        ELSE RAISE WARNING 'FAIL: Expected 5 dimension tables, found %', v_count; v_fail_count := v_fail_count + 1;
        END IF;
    END LOOP;

    -- CHECK 3: All fact tables exist
    RAISE NOTICE '--- FACT TABLE CHECKS ---';
    FOR v_count IN
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_schema = 'warehouse'
          AND table_name IN ('fact_customer_journey','fact_transactions','fact_product_events',
                             'fact_revenue','fact_marketing','fact_support','fact_kyc_events')
    LOOP
        IF v_count = 7 THEN RAISE NOTICE 'PASS: All 7 fact tables exist';
        ELSE RAISE WARNING 'FAIL: Expected 7 fact tables, found %', v_count; v_fail_count := v_fail_count + 1;
        END IF;
    END LOOP;

    -- CHECK 4: Seed data loaded
    RAISE NOTICE '--- SEED DATA CHECKS ---';
    SELECT COUNT(*) INTO v_count FROM warehouse.dim_country;
    IF v_count >= 20 THEN RAISE NOTICE 'PASS: dim_country has % rows', v_count;
    ELSE RAISE WARNING 'FAIL: dim_country has % rows (expected >= 20)', v_count; v_fail_count := v_fail_count + 1;
    END IF;

    SELECT COUNT(*) INTO v_count FROM warehouse.dim_product;
    IF v_count >= 10 THEN RAISE NOTICE 'PASS: dim_product has % rows', v_count;
    ELSE RAISE WARNING 'FAIL: dim_product has % rows (expected >= 10)', v_count; v_fail_count := v_fail_count + 1;
    END IF;

    SELECT COUNT(*) INTO v_count FROM warehouse.dim_channel;
    IF v_count >= 8 THEN RAISE NOTICE 'PASS: dim_channel has % rows', v_count;
    ELSE RAISE WARNING 'FAIL: dim_channel has % rows (expected >= 8)', v_count; v_fail_count := v_fail_count + 1;
    END IF;

    -- CHECK 5: Analytics views exist
    RAISE NOTICE '--- ANALYTICS VIEW CHECKS ---';
    FOR v_count IN
        SELECT COUNT(*) FROM information_schema.views
        WHERE table_schema = 'analytics'
          AND table_name IN (
            'v_monthly_business_summary','v_mau_trend','v_acquisition_funnel',
            'v_cohort_retention','v_product_adoption','v_revenue_by_geography',
            'v_kyc_performance','v_support_performance','v_customer_value','v_cac_by_channel'
          )
    LOOP
        IF v_count = 10 THEN RAISE NOTICE 'PASS: All 10 analytics views exist';
        ELSE RAISE WARNING 'FAIL: Expected 10 views, found %', v_count; v_fail_count := v_fail_count + 1;
        END IF;
    END LOOP;

    -- CHECK 6: Functions exist
    RAISE NOTICE '--- FUNCTION CHECKS ---';
    FOR v_count IN
        SELECT COUNT(*) FROM information_schema.routines
        WHERE routine_schema = 'warehouse'
          AND routine_name IN ('populate_dim_date','get_date_key','refresh_customer_lifecycle')
    LOOP
        IF v_count = 3 THEN RAISE NOTICE 'PASS: All 3 warehouse functions exist';
        ELSE RAISE WARNING 'FAIL: Expected 3 functions, found %', v_count; v_fail_count := v_fail_count + 1;
        END IF;
    END LOOP;

    -- CHECK 7: pipeline schema has version record
    SELECT COUNT(*) INTO v_count FROM pipeline.schema_version WHERE version = '2.0.0';
    IF v_count = 1 THEN RAISE NOTICE 'PASS: Sprint 2 schema version recorded';
    ELSE RAISE WARNING 'FAIL: Sprint 2 version record missing'; v_fail_count := v_fail_count + 1;
    END IF;

    -- SUMMARY
    RAISE NOTICE '--- RESULT ---';
    IF v_fail_count = 0 THEN
        RAISE NOTICE 'ALL CHECKS PASSED — Sprint 2 schema is production-ready';
    ELSE
        RAISE WARNING '% CHECK(S) FAILED — Review warnings above', v_fail_count;
    END IF;

END $$;
