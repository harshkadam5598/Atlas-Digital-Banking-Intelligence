#!/usr/bin/env bash
# ============================================================
# Atlas – Database Initialization Script
# Applies Sprint 2 schema in correct dependency order.
# ============================================================
set -euo pipefail

: "${POSTGRES_HOST:=localhost}"
: "${POSTGRES_PORT:=5432}"
: "${POSTGRES_DB:=atlas_db}"
: "${POSTGRES_USER:=atlas_user}"
: "${POSTGRES_PASSWORD:=atlas_password}"

export PGPASSWORD="$POSTGRES_PASSWORD"
PSQL="psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Atlas Database Initialization"
echo "  Host: $POSTGRES_HOST:$POSTGRES_PORT/$POSTGRES_DB"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

run_sql() {
    local file="$1"
    local label="$2"
    echo "  Applying: $label"
    $PSQL -f "$file" -q
    echo "  ✓ $label"
}

# Sprint 2: Schema in dependency order
run_sql "sql/schema/00_schemas.sql"          "Schema namespaces"
run_sql "sql/schema/01_dimensions.sql"        "Dimension tables"
run_sql "sql/schema/02_facts.sql"             "Fact tables"
run_sql "sql/schema/03_pipeline_tables.sql"   "Pipeline metadata tables"
run_sql "sql/schema/04_seed_data.sql"         "Reference / seed data"
run_sql "sql/schema/05_functions.sql"         "Stored functions"
run_sql "sql/indexes/01_performance_indexes.sql" "Performance indexes"
run_sql "sql/views/01_analytics_views.sql"    "Analytics views"

# Populate dim_date (3 years history + 90 days forward)
echo "  Populating dim_date..."
$PSQL -c "SELECT warehouse.populate_dim_date('2022-01-01', (CURRENT_DATE + INTERVAL '90 days')::date);" -q
echo "  ✓ dim_date populated"

# Validate
echo ""
echo "  Running validation checks..."
$PSQL -f "sql/validation/sprint2_validation.sql"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Database initialization complete."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
