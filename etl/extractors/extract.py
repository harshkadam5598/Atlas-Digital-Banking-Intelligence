"""
Atlas ETL – Extract Layer
Reads all Sprint 3 parquet files from data/raw/.
Validates schema compatibility against expected column contracts.
Logs extraction metrics into ETLContext.
"""

from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd
from loguru import logger

from etl.core.context import ETLContext, StageMetrics

# ── Expected schema contracts ─────────────────────────────────────────────────
# Maps table name → required columns. ETL rejects a file if any are missing.

SCHEMA_CONTRACTS: Dict[str, Dict[str, str]] = {
    "dim_customer": {
        "required": [
            "customer_id", "customer_uuid", "signup_date", "country_code",
            "channel_code", "age_group", "gender", "kyc_status",
            "lifecycle_stage", "premium_status", "is_test_customer",
        ],
        "date_cols": [
            "signup_date", "kyc_submission_date", "kyc_completion_date",
            "activation_date", "first_transaction_date", "premium_upgrade_date",
            "last_activity_date", "churn_date",
        ],
        "nullable": [
            "kyc_completion_date", "activation_date", "first_transaction_date",
            "premium_upgrade_date", "last_activity_date", "churn_date",
        ],
    },
    "fact_customer_journey": {
        "required": [
            "customer_id", "country_code", "channel_code", "signup_date",
            "reached_registration", "reached_kyc_submitted", "reached_kyc_approved",
            "reached_activation", "reached_first_deposit", "reached_premium",
            "is_churned", "kyc_outcome",
        ],
        "date_cols": [
            "signup_date", "kyc_submission_date", "kyc_completion_date",
            "activation_date", "first_transaction_date", "premium_upgrade_date",
            "churn_date",
        ],
        "nullable": [
            "kyc_completion_date", "activation_date", "first_transaction_date",
            "premium_upgrade_date", "churn_date",
            "days_to_kyc_completion", "days_to_activation", "days_to_premium",
        ],
    },
    "fact_transactions": {
        "required": [
            "customer_id", "product_code", "country_code", "transaction_date",
            "transaction_type", "amount_local", "currency_code", "currency_factor",
            "amount_gbp", "fee_amount_local", "fee_amount_gbp", "status",
        ],
        "date_cols": ["transaction_date"],
        "nullable": ["failure_reason"],
    },
    "fact_product_events": {
        "required": [
            "customer_id", "product_code", "country_code", "event_date", "event_type",
        ],
        "date_cols": ["event_date"],
        "nullable": ["device_type", "event_properties"],
    },
    "fact_revenue": {
        "required": [
            "customer_id", "product_code", "country_code", "transaction_date",
            "revenue_type", "gross_revenue_gbp", "net_revenue_gbp",
        ],
        "date_cols": ["transaction_date"],
        "nullable": [],
    },
    "fact_marketing": {
        "required": [
            "customer_id", "country_code", "channel_code", "touchpoint_date",
            "acquisition_cost_gbp", "is_converted",
        ],
        "date_cols": ["touchpoint_date", "conversion_date"],
        "nullable": ["conversion_date", "days_to_conversion"],
    },
    "fact_support": {
        "required": [
            "customer_id", "country_code", "created_date", "issue_type",
            "priority", "status", "resolution_time_hours",
        ],
        "date_cols": ["created_date", "resolved_date"],
        "nullable": ["resolved_date", "satisfaction_score"],
    },
    "fact_kyc_events": {
        "required": [
            "customer_id", "country_code", "submission_date", "kyc_type",
            "outcome", "attempt_number",
        ],
        "date_cols": ["submission_date", "completion_date"],
        "nullable": ["completion_date", "rejection_reason", "processing_time_hours"],
    },
}


# ── Extract ────────────────────────────────────────────────────────────────────

def extract_all(ctx: ETLContext) -> Dict[str, pd.DataFrame]:
    """
    Read all parquet files from raw_dir.
    Validate schema compatibility for each table.
    Returns dict of {table_name: DataFrame}.
    """
    stage = ctx.begin_stage("extract")
    raw_dir = ctx.raw_dir
    logger.info(f"[EXTRACT] Reading from {raw_dir}")

    result: Dict[str, pd.DataFrame] = {}
    total_rows = 0

    for table, contract in SCHEMA_CONTRACTS.items():
        path = raw_dir / f"{table}.parquet"
        if not path.exists():
            ctx.warn(f"Source file missing: {path.name}", "extract")
            logger.warning(f"  SKIP {table} — file not found")
            continue

        # Read
        df = pd.read_parquet(path)
        raw_rows = len(df)

        # Schema validation
        missing_cols = [c for c in contract["required"] if c not in df.columns]
        if missing_cols:
            msg = f"{table}: missing required columns {missing_cols}"
            ctx.error(msg, "extract")
            ctx.record_dq(False, "extract")
            logger.error(f"  FAIL {table} schema: {missing_cols}")
            continue
        ctx.record_dq(True, "extract")

        # Cast date columns immediately (str → date)
        for col in contract.get("date_cols", []):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce").dt.date

        result[table] = df
        total_rows += raw_rows
        ctx.log_audit(table, "extract", raw_rows)
        logger.info(f"  OK  {table:<30} {raw_rows:>8,} rows")

    stage.rows_in  = total_rows
    stage.rows_out = sum(len(v) for v in result.values())
    ctx.total_extracted = stage.rows_out
    ctx.end_stage("extract")

    logger.success(f"[EXTRACT] Complete: {len(result)} tables, "
                   f"{ctx.total_extracted:,} rows in {stage.duration_s}s")
    return result
