-- ============================================================
-- Atlas – Pipeline Metadata Tables
-- Schema: pipeline
-- ============================================================

CREATE TABLE IF NOT EXISTS pipeline.etl_run_log (
    run_id              BIGSERIAL       PRIMARY KEY,
    pipeline_name       VARCHAR(100)    NOT NULL,
    run_type            VARCHAR(20)     NOT NULL DEFAULT 'scheduled',  -- 'scheduled','manual','backfill'
    status              VARCHAR(20)     NOT NULL DEFAULT 'running',   -- 'running','success','failed','partial'
    started_at          TIMESTAMP       NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMP,
    duration_seconds    INTEGER,
    rows_extracted      BIGINT          DEFAULT 0,
    rows_transformed    BIGINT          DEFAULT 0,
    rows_loaded         BIGINT          DEFAULT 0,
    rows_failed         BIGINT          DEFAULT 0,
    error_message       TEXT,
    run_metadata        JSONB
);

COMMENT ON TABLE pipeline.etl_run_log IS 'ETL pipeline execution history. Used for monitoring, alerting, and data lineage.';

CREATE TABLE IF NOT EXISTS pipeline.data_quality_checks (
    check_id            BIGSERIAL       PRIMARY KEY,
    run_id              BIGINT          NOT NULL REFERENCES pipeline.etl_run_log(run_id),
    table_name          VARCHAR(100)    NOT NULL,
    check_name          VARCHAR(100)    NOT NULL,
    check_type          VARCHAR(30)     NOT NULL,  -- 'null_check','range_check','uniqueness','referential_integrity','row_count'
    expected_value      TEXT,
    actual_value        TEXT,
    passed              BOOLEAN         NOT NULL,
    checked_at          TIMESTAMP       NOT NULL DEFAULT NOW(),
    details             JSONB
);

COMMENT ON TABLE pipeline.data_quality_checks IS 'Row-level data quality check results per ETL run.';

CREATE TABLE IF NOT EXISTS pipeline.schema_version (
    version_id          SERIAL          PRIMARY KEY,
    version             VARCHAR(20)     NOT NULL,
    description         TEXT,
    applied_at          TIMESTAMP       NOT NULL DEFAULT NOW(),
    applied_by          VARCHAR(100)    NOT NULL DEFAULT CURRENT_USER,
    rollback_sql        TEXT
);

COMMENT ON TABLE pipeline.schema_version IS 'Manual schema version tracking (in addition to Alembic migrations).';

-- Insert Sprint 2 baseline version
INSERT INTO pipeline.schema_version (version, description)
VALUES ('2.0.0', 'Sprint 2: Initial star schema — dimensions, facts, pipeline tables')
ON CONFLICT DO NOTHING;
