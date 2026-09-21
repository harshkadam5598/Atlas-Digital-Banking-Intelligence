#!/usr/bin/env bash
# ============================================================
# Atlas – Docker Postgres Initialization Wrapper
# ============================================================
#
# Runs automatically via docker-entrypoint-initdb.d on first
# container start (official postgres image behavior — this only
# runs against an empty data directory; it will NOT re-run against
# an existing volume).
#
# This script does not define any SQL itself. It applies the
# existing SQL files under /atlas-sql (bind-mounted from the
# repository's sql/ directory — see docker-compose.yml) in the
# exact same dependency order as scripts/db_init.sh:
#   schema -> indexes -> views -> dim_date population -> validation
#
# Fixes a gap identified in the Phase 1 Deployment Readiness Audit:
# docker-compose previously mounted only sql/schema/ into
# docker-entrypoint-initdb.d, so a database brought up via
# `docker-compose up` alone had no indexes and — critically — none
# of the analytics views the API layer queries for every request.
#
# Not yet verified against a live Postgres instance in this
# environment (no Postgres server is available here — see the
# Phase 1A implementation report). This script is a direct,
# line-for-line translation of scripts/db_init.sh's already-used
# sequence into the docker-entrypoint-initdb.d context, so the
# same review that covers db_init.sh's correctness applies here;
# what specifically differs (and is therefore unverified) is the
# init-container environment itself: local-socket connection via
# $POSTGRES_USER/$POSTGRES_DB instead of db_init.sh's host/port/
# PGPASSWORD-based connection.

set -euo pipefail

SQL_DIR="/atlas-sql"
PSQL="psql -v ON_ERROR_STOP=1 --username ${POSTGRES_USER} --dbname ${POSTGRES_DB}"

echo "── Atlas: applying schema, indexes, and views ──"

run_sql() {
    local file="$1"
    local label="$2"
    echo "  Applying: ${label}"
    ${PSQL} -f "${file}" -q
}

# Same order as scripts/db_init.sh — kept in sync deliberately.
run_sql "${SQL_DIR}/schema/00_schemas.sql"          "Schema namespaces"
run_sql "${SQL_DIR}/schema/01_dimensions.sql"        "Dimension tables"
run_sql "${SQL_DIR}/schema/02_facts.sql"             "Fact tables"
run_sql "${SQL_DIR}/schema/03_pipeline_tables.sql"   "Pipeline metadata tables"
run_sql "${SQL_DIR}/schema/04_seed_data.sql"         "Reference / seed data"
run_sql "${SQL_DIR}/schema/05_functions.sql"         "Stored functions"
run_sql "${SQL_DIR}/indexes/01_performance_indexes.sql" "Performance indexes"
run_sql "${SQL_DIR}/views/01_analytics_views.sql"    "Analytics views (required by every API endpoint)"

echo "  Populating dim_date..."
${PSQL} -q -c "SELECT warehouse.populate_dim_date('2022-01-01', (CURRENT_DATE + INTERVAL '90 days')::date);"

echo "  Running validation checks (informational — see container logs for PASS/FAIL detail)..."
${PSQL} -f "${SQL_DIR}/validation/sprint2_validation.sql" -q || true

echo "── Atlas: database structure ready. No transactional data has been loaded — run the ETL pipeline separately. ──"
