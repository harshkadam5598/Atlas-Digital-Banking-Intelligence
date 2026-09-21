-- ============================================================
-- Atlas – Digital Banking Intelligence Platform
-- Schema Namespaces
-- ============================================================
-- Four schemas map to the four data warehouse zones.
-- Raw and staging are write-only from ETL; read-only from API.
-- Warehouse and analytics are what the API and dashboards query.
-- ============================================================

-- Raw zone: immutable source data as generated
CREATE SCHEMA IF NOT EXISTS raw;

-- Staging zone: cleansed, typed, deduped — no business logic yet
CREATE SCHEMA IF NOT EXISTS staging;

-- Warehouse zone: star schema (dimensions + facts)
CREATE SCHEMA IF NOT EXISTS warehouse;

-- Analytics zone: materialized KPI views served to API
CREATE SCHEMA IF NOT EXISTS analytics;

-- Pipeline metadata: ETL run logs, data quality reports
CREATE SCHEMA IF NOT EXISTS pipeline;

COMMENT ON SCHEMA raw       IS 'Immutable source layer. Never modified after insert.';
COMMENT ON SCHEMA staging   IS 'Cleaned, typed, deduped source data. No business logic.';
COMMENT ON SCHEMA warehouse IS 'Star schema: dimension and fact tables for OLAP queries.';
COMMENT ON SCHEMA analytics IS 'Materialized KPI views served directly to the API layer.';
COMMENT ON SCHEMA pipeline  IS 'ETL pipeline metadata: run logs, data quality, lineage.';
