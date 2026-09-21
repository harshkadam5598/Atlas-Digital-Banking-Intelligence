"""
Atlas ETL – Production Load Layer  (Sprint 4 Phase 2)

Architecture:
  Three-zone loading per table, executed in a single connection:
    1. raw.*       – verbatim source columns; business keys preserved
    2. staging.*   – fully typed, enriched transform output; no FK constraints
    3. warehouse.* – star-schema tables with surrogate FK resolution

Idempotency:
  Every table uses TRUNCATE + batch INSERT.
  dim_customer uses TRUNCATE CASCADE to clear all FK-dependent fact tables
  before reloading. Running the pipeline twice produces identical DB state.

Transaction model:
  - Zones 1 and 2 (raw + staging) share one connection/transaction.
  - Zone 3 (warehouse) uses a separate connection.
    dim_customer loads first and commits before any fact table begins —
    this satisfies the FK constraint that all fact rows reference valid
    customer_ids before they are inserted.
  - A table-level exception is caught, logged, and recorded in ETLContext;
    remaining tables continue. The operator reviews the ETL report.

Retry logic:
  _with_retry() wraps any load call with configurable attempts and
  exponential back-off. Default: 3 attempts, 2s initial delay, 2x back-off.
  Retries are applied at the table level, not the batch level.

Bulk optimisation:
  - psycopg2.extras.execute_batch with page_size == BATCH_SIZE (5 000)
  - _df_to_rows replaces ALL NA variants (NaN, NaT, pd.NA, None)
    with Python None before the insert, including pandas NaTType which
    itertuples() surfaces as <NaTType> rather than None.
  - Columns absent from the DataFrame are silently skipped.

Connection:
  Reads POSTGRES_* env vars; falls back to docker-compose defaults.
"""

import json
import os
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

import pandas as pd
import psycopg2
import psycopg2.extras
from loguru import logger

from etl.core.context import ETLContext

# ── Connection ─────────────────────────────────────────────────────────────────

def _get_conn_params() -> Dict[str, Any]:
    return {
        "host":            os.getenv("POSTGRES_HOST",     "localhost"),
        "port":            int(os.getenv("POSTGRES_PORT", "5432")),
        "dbname":          os.getenv("POSTGRES_DB",       "atlas_db"),
        "user":            os.getenv("POSTGRES_USER",     "atlas_user"),
        "password":        os.getenv("POSTGRES_PASSWORD", "atlas_password"),
        "connect_timeout": 10,
    }


@contextmanager
def get_connection() -> Generator:
    """
    Yields a psycopg2 connection with autocommit=False.
    Commits on clean exit; rolls back and re-raises on any exception.
    """
    conn = psycopg2.connect(**_get_conn_params())
    conn.autocommit = False
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def check_db_available() -> bool:
    """Probe the database. Returns True if reachable, False otherwise."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        logger.info("Database connectivity confirmed")
        return True
    except Exception as e:
        logger.warning(f"Database not available: {e}")
        return False


# ── Retry helper ───────────────────────────────────────────────────────────────

def _with_retry(fn: Callable, table: str,
                max_attempts: int = 3,
                base_delay_s: float = 2.0,
                backoff: float = 2.0) -> Any:
    """
    Execute fn() with exponential back-off retry.
    Retries on psycopg2.OperationalError (transient connection loss).
    Does NOT retry on ProgrammingError or IntegrityError (schema bugs,
    constraint violations) — those require operator intervention.
    """
    delay = base_delay_s
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except psycopg2.OperationalError as e:
            if attempt == max_attempts:
                logger.error(f"[LOAD] {table}: all {max_attempts} attempts failed: {e}")
                raise
            logger.warning(
                f"[LOAD] {table}: attempt {attempt}/{max_attempts} failed "
                f"({e}). Retrying in {delay:.1f}s…"
            )
            time.sleep(delay)
            delay *= backoff
        except (psycopg2.ProgrammingError, psycopg2.IntegrityError):
            # Schema mismatch or constraint violation — not retriable
            raise


# ── Row conversion ─────────────────────────────────────────────────────────────

def _df_to_rows(df: pd.DataFrame, columns: List[str]) -> List[tuple]:
    """
    Convert a DataFrame subset to a list of plain Python tuples.

    Converts ALL NA-family values to Python None so psycopg2 writes SQL NULL:
      - float NaN
      - pandas NaT  (both NaTType and pd.NaT)
      - None / pd.NA

    datetime.date objects (produced by Extract's dt.date cast) are passed
    through unchanged — psycopg2 maps them to PostgreSQL DATE natively.
    """
    present = [c for c in columns if c in df.columns]
    rows: List[tuple] = []
    for tup in df[present].itertuples(index=False, name=None):
        cleaned = tuple(
            None if (
                v is None
                or v is pd.NaT
                or v is pd.NA
                or (isinstance(v, float) and v != v)          # NaN
                or type(v).__name__ == "NaTType"               # pd NaTType
            ) else v
            for v in tup
        )
        rows.append(cleaned)
    return rows


# ── Batch insert ───────────────────────────────────────────────────────────────

BATCH_SIZE = 5_000


def _batch_insert(cur,
                  qualified_table: str,
                  columns: List[str],
                  rows: List[tuple],
                  on_conflict: str = "DO NOTHING") -> int:
    """
    Bulk-insert rows into qualified_table using execute_batch.

    ON CONFLICT DO NOTHING is the default: duplicate primary keys are
    silently skipped. Use on_conflict="DO UPDATE …" for upsert semantics
    if ever needed (not required for TRUNCATE+INSERT idempotency pattern).

    Returns the number of rows sent (not affected — skipped rows count too).
    """
    if not rows:
        return 0
    placeholders = ",".join(["%s"] * len(columns))
    col_list     = ",".join(columns)
    sql = (
        f"INSERT INTO {qualified_table} ({col_list}) "
        f"VALUES ({placeholders}) ON CONFLICT {on_conflict}"
    )
    sent = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        psycopg2.extras.execute_batch(cur, sql, batch, page_size=BATCH_SIZE)
        sent += len(batch)
    return sent


# ── Raw schema DDL ─────────────────────────────────────────────────────────────

def _ensure_raw_schema(cur) -> None:
    """
    Create raw.* tables for verbatim source storage.
    Uses CREATE TABLE IF NOT EXISTS — idempotent, safe to call on every run.
    Raw tables preserve business keys (codes, not surrogate IDs).
    """
    cur.execute("""
        CREATE TABLE IF NOT EXISTS raw.dim_customer_raw (
            customer_id      BIGINT,
            customer_uuid    TEXT,
            signup_date      DATE,
            country_code     CHAR(2),
            channel_code     VARCHAR(30),
            kyc_status       VARCHAR(20),
            lifecycle_stage  VARCHAR(30),
            premium_status   BOOLEAN,
            age_group        VARCHAR(20),
            gender           VARCHAR(20),
            income_band      VARCHAR(30),
            device_type      VARCHAR(20),
            loaded_at        TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS raw.fact_transactions_raw (
            customer_id       BIGINT,
            product_code      VARCHAR(30),
            country_code      CHAR(2),
            transaction_date  DATE,
            transaction_type  VARCHAR(30),
            amount_local      NUMERIC(14,2),
            currency_code     CHAR(3),
            amount_gbp        NUMERIC(14,2),
            fee_amount_gbp    NUMERIC(10,2),
            status            VARCHAR(20),
            loaded_at         TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS raw.fact_product_events_raw (
            customer_id   BIGINT,
            product_code  VARCHAR(30),
            country_code  CHAR(2),
            event_date    DATE,
            event_type    VARCHAR(50),
            device_type   VARCHAR(20),
            loaded_at     TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS raw.fact_support_raw (
            customer_id           BIGINT,
            country_code          CHAR(2),
            created_date          DATE,
            issue_type            VARCHAR(50),
            priority              VARCHAR(10),
            status                VARCHAR(20),
            resolution_time_hours NUMERIC(8,2),
            satisfaction_score    SMALLINT,
            loaded_at             TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS raw.fact_kyc_events_raw (
            customer_id           BIGINT,
            country_code          CHAR(2),
            submission_date       DATE,
            kyc_type              VARCHAR(30),
            outcome               VARCHAR(20),
            processing_time_hours NUMERIC(8,2),
            attempt_number        SMALLINT,
            loaded_at             TIMESTAMP DEFAULT NOW()
        )
    """)


# ── Staging schema DDL ─────────────────────────────────────────────────────────

def _ensure_staging_schema(cur) -> None:
    """
    Create staging.* tables mirroring warehouse schema but without FK constraints.
    Staging holds the exact output of the Transform layer.
    Uses CREATE TABLE IF NOT EXISTS — idempotent.
    """
    cur.execute("""
        CREATE TABLE IF NOT EXISTS staging.dim_customer_staged (
            customer_id            BIGINT PRIMARY KEY,
            customer_uuid          UUID,
            signup_date            DATE,
            signup_date_key        INTEGER,
            country_code           CHAR(2),
            country_id             INTEGER,
            channel_code           VARCHAR(30),
            channel_id             INTEGER,
            age_group              VARCHAR(20),
            gender                 VARCHAR(20),
            occupation             VARCHAR(50),
            income_band            VARCHAR(30),
            device_type            VARCHAR(20),
            kyc_status             VARCHAR(20),
            kyc_submission_date    DATE,
            kyc_completion_date    DATE,
            activation_date        DATE,
            first_transaction_date DATE,
            premium_upgrade_date   DATE,
            last_activity_date     DATE,
            churn_date             DATE,
            lifecycle_stage        VARCHAR(30),
            premium_status         BOOLEAN,
            customer_segment       VARCHAR(30),
            clv_band               VARCHAR(20),
            churn_risk_score       NUMERIC(5,2),
            product_count          SMALLINT,
            total_revenue_gbp      NUMERIC(12,2),
            is_test_customer       BOOLEAN,
            staged_at              TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS staging.fact_transactions_staged (
            customer_id            BIGINT,
            product_id             INTEGER,
            country_id             INTEGER,
            transaction_date_key   INTEGER,
            transaction_date       DATE,
            transaction_timestamp  TIMESTAMP,
            transaction_type       VARCHAR(30),
            amount_local           NUMERIC(14,2),
            currency_code          CHAR(3),
            currency_factor        NUMERIC(10,6),
            amount_gbp             NUMERIC(14,2),
            fee_amount_local       NUMERIC(10,2),
            fee_amount_gbp         NUMERIC(10,2),
            status                 VARCHAR(20),
            failure_reason         VARCHAR(100),
            is_premium_customer    BOOLEAN,
            staged_at              TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS staging.fact_product_events_staged (
            customer_id      BIGINT,
            product_id       INTEGER,
            country_id       INTEGER,
            event_date_key   INTEGER,
            event_date       DATE,
            event_timestamp  TIMESTAMP,
            event_type       VARCHAR(50),
            event_properties TEXT,
            device_type      VARCHAR(20),
            staged_at        TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS staging.fact_revenue_staged (
            customer_id        BIGINT,
            product_id         INTEGER,
            country_id         INTEGER,
            revenue_date_key   INTEGER,
            revenue_date       DATE,
            revenue_type       VARCHAR(30),
            gross_revenue_gbp  NUMERIC(12,2),
            refunds_gbp        NUMERIC(12,2),
            net_revenue_gbp    NUMERIC(12,2),
            transaction_count  INTEGER,
            is_premium_revenue BOOLEAN,
            staged_at          TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS staging.fact_kyc_events_staged (
            customer_id              BIGINT,
            country_id               INTEGER,
            submission_date_key      INTEGER,
            submission_date          DATE,
            submission_timestamp     TIMESTAMP,
            completion_date          DATE,
            kyc_type                 VARCHAR(30),
            outcome                  VARCHAR(20),
            rejection_reason         VARCHAR(100),
            processing_time_hours    NUMERIC(8,2),
            is_resubmission          BOOLEAN,
            attempt_number           SMALLINT,
            staged_at                TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS staging.fact_support_staged (
            customer_id              BIGINT,
            country_id               INTEGER,
            created_date_key         INTEGER,
            created_date             DATE,
            resolved_date            DATE,
            issue_type               VARCHAR(50),
            priority                 VARCHAR(10),
            status                   VARCHAR(20),
            channel                  VARCHAR(20),
            resolution_time_hours    NUMERIC(8,2),
            first_response_time_hrs  NUMERIC(8,2),
            satisfaction_score       SMALLINT,
            is_premium_customer      BOOLEAN,
            staged_at                TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS staging.fact_marketing_staged (
            customer_id            BIGINT,
            channel_id             INTEGER,
            country_id             INTEGER,
            touchpoint_date_key    INTEGER,
            touchpoint_date        DATE,
            campaign_id            VARCHAR(50),
            campaign_name          VARCHAR(150),
            acquisition_cost_gbp   NUMERIC(8,2),
            is_converted           BOOLEAN,
            conversion_date        DATE,
            days_to_conversion     SMALLINT,
            staged_at              TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS staging.fact_customer_journey_staged (
            customer_id                BIGINT PRIMARY KEY,
            country_id                 INTEGER,
            channel_id                 INTEGER,
            signup_date_key            INTEGER,
            signup_date                DATE,
            kyc_submission_date        DATE,
            kyc_completion_date        DATE,
            activation_date            DATE,
            first_transaction_date     DATE,
            premium_upgrade_date       DATE,
            churn_date                 DATE,
            days_to_kyc_submission     SMALLINT,
            days_to_kyc_completion     SMALLINT,
            days_to_activation         SMALLINT,
            days_to_premium            INTEGER,
            reached_registration       BOOLEAN,
            reached_kyc_submitted      BOOLEAN,
            reached_kyc_approved       BOOLEAN,
            reached_activation         BOOLEAN,
            reached_first_deposit      BOOLEAN,
            reached_premium            BOOLEAN,
            is_churned                 BOOLEAN,
            kyc_outcome                VARCHAR(20),
            staged_at                  TIMESTAMP DEFAULT NOW()
        )
    """)


# ── Raw zone loaders ───────────────────────────────────────────────────────────

def _load_raw_zone(transformed: Dict[str, pd.DataFrame], cur) -> Dict[str, int]:
    """Load verbatim (business-key) source data into raw.* tables."""
    counts: Dict[str, int] = {}

    _raw_specs: List[Tuple[str, str, List[str]]] = [
        ("dim_customer", "raw.dim_customer_raw", [
            "customer_id", "customer_uuid", "signup_date", "country_code",
            "channel_code", "kyc_status", "lifecycle_stage", "premium_status",
            "age_group", "gender", "income_band", "device_type",
        ]),
        ("fact_transactions", "raw.fact_transactions_raw", [
            "customer_id", "product_code", "country_code", "transaction_date",
            "transaction_type", "amount_local", "currency_code",
            "amount_gbp", "fee_amount_gbp", "status",
        ]),
        ("fact_product_events", "raw.fact_product_events_raw", [
            "customer_id", "product_code", "country_code",
            "event_date", "event_type", "device_type",
        ]),
        ("fact_support", "raw.fact_support_raw", [
            "customer_id", "country_code", "created_date", "issue_type",
            "priority", "status", "resolution_time_hours", "satisfaction_score",
        ]),
        ("fact_kyc_events", "raw.fact_kyc_events_raw", [
            "customer_id", "country_code", "submission_date", "kyc_type",
            "outcome", "processing_time_hours", "attempt_number",
        ]),
    ]

    for src, target, cols in _raw_specs:
        if src not in transformed:
            continue
        cur.execute(f"TRUNCATE {target}")
        df    = transformed[src]
        avail = [c for c in cols if c in df.columns]
        rows  = _df_to_rows(df, avail)
        n     = _batch_insert(cur, target, avail, rows)
        counts[target] = n

    return counts


# ── Staging zone loaders ───────────────────────────────────────────────────────

def _load_staging_zone(transformed: Dict[str, pd.DataFrame], cur) -> Dict[str, int]:
    """Load complete transformed output into staging.* tables."""
    counts: Dict[str, int] = {}

    _staging_specs: List[Tuple[str, str, List[str]]] = [
        ("dim_customer", "staging.dim_customer_staged", [
            "customer_id", "customer_uuid", "signup_date", "signup_date_key",
            "country_code", "country_id", "channel_code", "channel_id",
            "age_group", "gender", "occupation", "income_band", "device_type",
            "kyc_status", "kyc_submission_date", "kyc_completion_date",
            "activation_date", "first_transaction_date", "premium_upgrade_date",
            "last_activity_date", "churn_date", "lifecycle_stage",
            "premium_status", "customer_segment", "clv_band", "churn_risk_score",
            "product_count", "total_revenue_gbp", "is_test_customer",
        ]),
        ("fact_customer_journey", "staging.fact_customer_journey_staged", [
            "customer_id", "country_id", "channel_id", "signup_date_key",
            "signup_date", "kyc_submission_date", "kyc_completion_date",
            "activation_date", "first_transaction_date", "premium_upgrade_date",
            "churn_date", "days_to_kyc_submission", "days_to_kyc_completion",
            "days_to_activation", "days_to_premium", "reached_registration",
            "reached_kyc_submitted", "reached_kyc_approved", "reached_activation",
            "reached_first_deposit", "reached_premium", "is_churned", "kyc_outcome",
        ]),
        ("fact_transactions", "staging.fact_transactions_staged", [
            "customer_id", "product_id", "country_id", "transaction_date_key",
            "transaction_date", "transaction_timestamp", "transaction_type",
            "amount_local", "currency_code", "currency_factor", "amount_gbp",
            "fee_amount_local", "fee_amount_gbp", "status", "failure_reason",
            "is_premium_customer",
        ]),
        ("fact_product_events", "staging.fact_product_events_staged", [
            "customer_id", "product_id", "country_id", "event_date_key",
            "event_date", "event_timestamp", "event_type",
            "event_properties", "device_type",
        ]),
        ("fact_revenue", "staging.fact_revenue_staged", [
            "customer_id", "product_id", "country_id", "revenue_date_key",
            "revenue_date", "revenue_type", "gross_revenue_gbp", "refunds_gbp",
            "net_revenue_gbp", "transaction_count", "is_premium_revenue",
        ]),
        ("fact_marketing", "staging.fact_marketing_staged", [
            "customer_id", "channel_id", "country_id", "touchpoint_date_key",
            "touchpoint_date", "campaign_id", "campaign_name",
            "acquisition_cost_gbp", "is_converted", "conversion_date",
            "days_to_conversion",
        ]),
        ("fact_support", "staging.fact_support_staged", [
            "customer_id", "country_id", "created_date_key", "created_date",
            "resolved_date", "issue_type", "priority", "status", "channel",
            "resolution_time_hours", "first_response_time_hrs",
            "satisfaction_score", "is_premium_customer",
        ]),
        ("fact_kyc_events", "staging.fact_kyc_events_staged", [
            "customer_id", "country_id", "submission_date_key", "submission_date",
            "submission_timestamp", "completion_date", "kyc_type", "outcome",
            "rejection_reason", "processing_time_hours",
            "is_resubmission", "attempt_number",
        ]),
    ]

    for src, target, cols in _staging_specs:
        if src not in transformed:
            continue
        cur.execute(f"TRUNCATE {target} CASCADE" if "dim_customer" in target else f"TRUNCATE {target}")
        df    = transformed[src]
        avail = [c for c in cols if c in df.columns]
        rows  = _df_to_rows(df, avail)
        n     = _batch_insert(cur, target, avail, rows)
        counts[target] = n

    return counts


# ── Warehouse zone loaders ─────────────────────────────────────────────────────

def load_dim_customer(df: pd.DataFrame, cur) -> int:
    cur.execute("TRUNCATE warehouse.dim_customer CASCADE")
    cols = [
        "customer_id", "customer_uuid", "signup_date", "signup_date_key",
        "country_id", "channel_id", "age_group", "gender", "occupation",
        "income_band", "device_type", "kyc_status", "kyc_submission_date",
        "kyc_completion_date", "activation_date", "first_transaction_date",
        "premium_upgrade_date", "last_activity_date", "churn_date",
        "lifecycle_stage", "premium_status", "customer_segment", "clv_band",
        "churn_risk_score", "product_count", "total_revenue_gbp",
        "is_test_customer",
    ]
    avail = [c for c in cols if c in df.columns]
    return _batch_insert(cur, "warehouse.dim_customer", avail,
                         _df_to_rows(df, avail))


def load_fact_customer_journey(df: pd.DataFrame, cur) -> int:
    cur.execute("TRUNCATE warehouse.fact_customer_journey CASCADE")
    cols = [
        "customer_id", "country_id", "channel_id", "signup_date_key",
        "signup_date", "kyc_submission_date", "kyc_completion_date",
        "activation_date", "first_transaction_date", "premium_upgrade_date",
        "churn_date", "days_to_kyc_submission", "days_to_kyc_completion",
        "days_to_activation", "days_to_premium", "reached_registration",
        "reached_kyc_submitted", "reached_kyc_approved", "reached_activation",
        "reached_first_deposit", "reached_premium", "is_churned", "kyc_outcome",
    ]
    avail = [c for c in cols if c in df.columns]
    return _batch_insert(cur, "warehouse.fact_customer_journey", avail,
                         _df_to_rows(df, avail))


def load_fact_transactions(df: pd.DataFrame, cur) -> int:
    cur.execute("TRUNCATE warehouse.fact_transactions")
    cols = [
        "customer_id", "product_id", "country_id", "transaction_date_key",
        "transaction_date", "transaction_timestamp", "transaction_type",
        "amount_local", "currency_code", "currency_factor", "amount_gbp",
        "fee_amount_local", "fee_amount_gbp", "merchant_name",
        "merchant_category", "status", "failure_reason",
        "customer_segment", "is_premium_customer",
    ]
    avail = [c for c in cols if c in df.columns]
    return _batch_insert(cur, "warehouse.fact_transactions", avail,
                         _df_to_rows(df, avail))


def load_fact_product_events(df: pd.DataFrame, cur) -> int:
    cur.execute("TRUNCATE warehouse.fact_product_events")
    cols = [
        "customer_id", "product_id", "country_id", "event_date_key",
        "event_date", "event_timestamp", "event_type",
        "event_properties", "device_type",
    ]
    avail = [c for c in cols if c in df.columns]
    return _batch_insert(cur, "warehouse.fact_product_events", avail,
                         _df_to_rows(df, avail))


def load_fact_revenue(df: pd.DataFrame, cur) -> int:
    cur.execute("TRUNCATE warehouse.fact_revenue")
    cols = [
        "customer_id", "product_id", "country_id", "revenue_date_key",
        "revenue_date", "revenue_type", "gross_revenue_gbp", "refunds_gbp",
        "net_revenue_gbp", "transaction_count", "is_premium_revenue",
    ]
    avail = [c for c in cols if c in df.columns]
    return _batch_insert(cur, "warehouse.fact_revenue", avail,
                         _df_to_rows(df, avail))


def load_fact_marketing(df: pd.DataFrame, cur) -> int:
    cur.execute("TRUNCATE warehouse.fact_marketing")
    cols = [
        "customer_id", "channel_id", "country_id", "touchpoint_date_key",
        "campaign_id", "campaign_name", "touchpoint_date",
        "acquisition_cost_gbp", "is_converted", "conversion_date",
        "days_to_conversion",
    ]
    avail = [c for c in cols if c in df.columns]
    return _batch_insert(cur, "warehouse.fact_marketing", avail,
                         _df_to_rows(df, avail))


def load_fact_support(df: pd.DataFrame, cur) -> int:
    cur.execute("TRUNCATE warehouse.fact_support")
    cols = [
        "customer_id", "country_id", "created_date_key", "created_at",
        "resolved_at", "first_response_at", "issue_type", "priority",
        "status", "channel", "resolution_time_hours",
        "first_response_time_hrs", "satisfaction_score",
        "is_premium_customer", "created_date",
    ]
    avail = [c for c in cols if c in df.columns]
    return _batch_insert(cur, "warehouse.fact_support", avail,
                         _df_to_rows(df, avail))


def load_fact_kyc_events(df: pd.DataFrame, cur) -> int:
    cur.execute("TRUNCATE warehouse.fact_kyc_events")
    cols = [
        "customer_id", "country_id", "submission_date_key", "submission_date",
        "submission_timestamp", "completion_timestamp", "kyc_type", "outcome",
        "rejection_reason", "processing_time_hours",
        "is_resubmission", "attempt_number",
    ]
    avail = [c for c in cols if c in df.columns]
    return _batch_insert(cur, "warehouse.fact_kyc_events", avail,
                         _df_to_rows(df, avail))


# ── Analytics view verification ────────────────────────────────────────────────

ANALYTICS_VIEWS = [
    "analytics.v_monthly_business_summary",
    "analytics.v_mau_trend",
    "analytics.v_acquisition_funnel",
    "analytics.v_cohort_retention",
    "analytics.v_product_adoption",
    "analytics.v_revenue_by_geography",
    "analytics.v_kyc_performance",
    "analytics.v_support_performance",
    "analytics.v_customer_value",
    "analytics.v_cac_by_channel",
]


def refresh_analytics_views(conn) -> Dict[str, int]:
    """
    Verify all 10 analytics views are queryable after warehouse load.
    Views are live SQL (not materialised) — no explicit refresh required.
    Returns {view_name: row_count}.
    """
    view_counts: Dict[str, int] = {}
    with conn.cursor() as cur:
        for view in ANALYTICS_VIEWS:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {view}")
                n = cur.fetchone()[0]
                view_counts[view] = n
                logger.info(f"  VIEW  {view:<48} {n:>7,} rows")
            except Exception as e:
                view_counts[view] = -1
                logger.warning(f"  VIEW  {view} not queryable: {e}")
    return view_counts


# ── ETL run log ────────────────────────────────────────────────────────────────

def log_etl_run(conn, ctx: ETLContext, warehouse_total: int) -> None:
    """
    Insert a record into pipeline.etl_run_log for this pipeline execution.
    warehouse_total: the number of rows successfully loaded into warehouse.*.

    The function accepts warehouse_total as an explicit argument rather than
    reading ctx.total_loaded because log_etl_run is called before
    ctx.total_loaded is finalised (ctx.end_stage("load") fires after this).
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO pipeline.etl_run_log
                    (pipeline_name, run_type, status, started_at, completed_at,
                     duration_seconds, rows_extracted, rows_transformed,
                     rows_loaded, rows_failed, run_metadata)
                VALUES (%s, %s, %s, %s, NOW(), %s, %s, %s, %s, %s, %s::jsonb)
            """, (
                "atlas_etl_sprint4",
                "scheduled",
                ctx.overall_status,
                ctx.started_at,
                int(ctx.elapsed_seconds),
                ctx.total_extracted,
                ctx.total_transformed,
                warehouse_total,
                ctx.total_rejected,
                json.dumps({
                    "run_id":     ctx.run_id,
                    "dq_score":   ctx.data_quality_score,
                    "source_ver": ctx.source_version,
                    "warnings":   len(ctx.warnings),
                    "errors":     len(ctx.errors),
                }),
            ))
        conn.commit()
        logger.info("ETL run logged → pipeline.etl_run_log")
    except Exception as e:
        logger.warning(f"Could not write ETL run log: {e}")


# ── Load order ─────────────────────────────────────────────────────────────────

WAREHOUSE_LOAD_ORDER: List[Tuple[str, Callable]] = [
    ("dim_customer",          load_dim_customer),
    ("fact_customer_journey", load_fact_customer_journey),
    ("fact_transactions",     load_fact_transactions),
    ("fact_product_events",   load_fact_product_events),
    ("fact_revenue",          load_fact_revenue),
    ("fact_marketing",        load_fact_marketing),
    ("fact_support",          load_fact_support),
    ("fact_kyc_events",       load_fact_kyc_events),
]

# Backwards-compatible alias used by existing validate.py import
LOAD_ORDER = WAREHOUSE_LOAD_ORDER


# ── Main orchestrator ──────────────────────────────────────────────────────────

def load_all(
    transformed: Dict[str, pd.DataFrame],
    ctx: ETLContext,
    db_available: bool = True,
) -> Dict[str, int]:
    """
    Execute the three-zone load: raw → staging → warehouse.

    Zone 1 (raw) and Zone 2 (staging) share one connection/transaction.
    Zone 3 (warehouse) uses a separate connection; dim_customer commits first
    so FK constraints are satisfied before any fact table begins inserting.

    Each warehouse table load is individually retried up to 3 times on
    transient OperationalError. Non-retriable errors (schema, constraint)
    are logged and recorded in ctx.errors without aborting other tables.

    Returns a combined {table_or_zone_key: rows_loaded} dict for all zones.
    """
    stage = ctx.begin_stage("load")
    loaded_counts: Dict[str, int] = {}

    # ── Dry-run / no DB path ──────────────────────────────────────────────────
    if not db_available:
        ctx.warn("Database not available — load stage SKIPPED (dry-run mode)", "load")
        logger.warning("[LOAD] Skipping — PostgreSQL not reachable")
        for table, _ in WAREHOUSE_LOAD_ORDER:
            if table in transformed:
                loaded_counts[table] = 0
                logger.info(
                    f"  DRY-RUN  {table:<32} "
                    f"{len(transformed[table]):>7,} rows would load"
                )
        stage.rows_in  = sum(len(transformed[t]) for t in transformed)
        stage.rows_out = 0
        ctx.total_loaded = 0
        ctx.end_stage("load")
        return loaded_counts

    logger.info("[LOAD] Starting three-zone load: raw → staging → warehouse")
    warehouse_total = 0

    # ── Zones 1 + 2: raw and staging (single transaction) ────────────────────
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                logger.info("[LOAD] Zone 1: raw.*")
                _ensure_raw_schema(cur)
                raw_counts = _load_raw_zone(transformed, cur)
                for tbl, n in raw_counts.items():
                    logger.info(f"  raw   {tbl:<42} {n:>7,} rows")
                    loaded_counts[tbl] = n
                    ctx.log_audit(tbl, "load_raw", n)

                logger.info("[LOAD] Zone 2: staging.*")
                _ensure_staging_schema(cur)
                stg_counts = _load_staging_zone(transformed, cur)
                for tbl, n in stg_counts.items():
                    logger.info(f"  stg   {tbl:<42} {n:>7,} rows")
                    loaded_counts[tbl] = n
                    ctx.log_audit(tbl, "load_staging", n)

    except Exception as e:
        msg = f"Raw/staging load failed: {e}"
        ctx.error(msg, "load")
        logger.error(f"[LOAD] {msg}")
        # Continue to warehouse zone — it has its own connection

    # ── Zone 3: warehouse (dim first, then facts, each with retry) ───────────
    logger.info("[LOAD] Zone 3: warehouse.*")
    for table, loader_fn in WAREHOUSE_LOAD_ORDER:
        if table not in transformed:
            continue
        df = transformed[table]

        def _do_load(df=df, loader_fn=loader_fn, table=table) -> int:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    n = loader_fn(df, cur)
            return n

        try:
            n = _with_retry(_do_load, table)
            loaded_counts[table] = n
            warehouse_total += n
            ctx.log_audit(table, "load_warehouse", n, "TRUNCATE+INSERT idempotent")
            logger.info(f"  wh    warehouse.{table:<30} {n:>7,} rows")
        except Exception as e:
            msg = f"Warehouse load failed [{table}]: {e}"
            ctx.error(msg, "load")
            logger.error(f"  FAIL  {table}: {e}")

    # ── Analytics view verification ───────────────────────────────────────────
    logger.info("[LOAD] Verifying analytics views")
    try:
        with get_connection() as conn:
            view_counts = refresh_analytics_views(conn)
            view_failures = [v for v, n in view_counts.items() if n < 0]
            if view_failures:
                ctx.warn(f"{len(view_failures)} analytics view(s) not queryable: "
                         f"{view_failures}", "load")
    except Exception as e:
        ctx.warn(f"Analytics view verification failed: {e}", "load")

    # ── ETL run log ───────────────────────────────────────────────────────────
    try:
        with get_connection() as conn:
            log_etl_run(conn, ctx, warehouse_total)
    except Exception as e:
        ctx.warn(f"ETL run log write failed: {e}", "load")

    # ── Finalise stage metrics ────────────────────────────────────────────────
    stage.rows_in    = sum(len(transformed[t]) for t in transformed)
    stage.rows_out   = warehouse_total
    ctx.total_loaded = warehouse_total
    ctx.end_stage("load")

    logger.success(
        f"[LOAD] Complete: {warehouse_total:,} warehouse rows  "
        f"| {stage.duration_s}s"
    )
    return loaded_counts
