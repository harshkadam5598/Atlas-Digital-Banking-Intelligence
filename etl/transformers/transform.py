"""
Atlas ETL – Transform Layer
Applies all business-rule transformations per table.
Operations (in order per table):
  1. Data type normalisation
  2. Null handling (fill / reject based on nullable contract)
  3. Deduplication
  4. Business rule validation (BR-001 through BR-014)
  5. Feature engineering (surrogate key resolution, date_key derivation)
  6. Reject tracking (rows failing hard rules go to reject log)

Output: cleaned DataFrames ready for warehouse loading.
"""

import json
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger

from etl.core.context import ETLContext

# ── Lookup tables (seeded in Sprint 2) ────────────────────────────────────────
# These mirror exactly what's in sql/schema/04_seed_data.sql

COUNTRY_MAP: Dict[str, int] = {
    "GB":1,"DE":2,"FR":3,"NL":4,"IE":5,"ES":6,"IT":7,"PT":8,
    "SE":9,"NO":10,"DK":11,"FI":12,"PL":13,"RO":14,"CZ":15,"HU":16,
    "US":17,"CA":18,"BR":19,"AU":20,"SG":21,"JP":22,
}

CHANNEL_MAP: Dict[str, int] = {
    "ORGANIC_SEARCH":1,"REFERRAL":2,"GOOGLE_ADS":3,"SOCIAL_META":4,
    "SOCIAL_TIKTOK":5,"INFLUENCER":6,"EMAIL":7,"DIRECT":8,
}

PRODUCT_MAP: Dict[str, int] = {
    "DEBIT_CARD":1,"PREMIUM_SUB":2,"SAVINGS_BASIC":3,"SAVINGS_VAULT":4,
    "INVEST_BASIC":5,"INVEST_PREMIUM":6,"FX_STANDARD":7,
    "TRANSFER_INT":8,"TRANSFER_FREE":9,"CRYPTO":10,
}

VALID_KYC_STATUS       = {"approved","rejected","pending"}
VALID_LIFECYCLE_STAGES = {"registered","kyc_pending","kyc_rejected","activated","churned","reactivated"}
VALID_TXN_STATUS       = {"completed","failed","pending","reversed"}
VALID_PRIORITIES       = {"P1","P2","P3"}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _date_to_key(d) -> Optional[int]:
    """Convert a date to YYYYMMDD integer key. Returns None if null."""
    if d is None or (isinstance(d, float) and np.isnan(d)):
        return None
    try:
        if isinstance(d, (datetime, date)):
            return int(d.strftime("%Y%m%d"))
        return int(pd.to_datetime(d).strftime("%Y%m%d"))
    except Exception:
        return None


def _reject(df: pd.DataFrame, mask: pd.Series, reason: str,
            rejects: List[Dict]) -> pd.DataFrame:
    """Separate rejected rows, add to rejects list, return clean rows."""
    bad = df[mask].copy()
    bad["_reject_reason"] = reason
    rejects.extend(bad.to_dict("records"))
    return df[~mask].copy()


def _to_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce").dt.date


def _safe_int(series: pd.Series, fill: int = 0) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(fill).astype(int)


def _safe_float(series: pd.Series, fill: float = 0.0) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(fill).astype(float)


# ── Per-table transformers ─────────────────────────────────────────────────────

def transform_dim_customer(df: pd.DataFrame, ctx: ETLContext,
                            rejects: List[Dict]) -> pd.DataFrame:
    stage = "transform_dim_customer"
    n_in = len(df)

    # 1. Type normalisation
    df["customer_id"]    = _safe_int(df["customer_id"])
    df["product_count"]  = _safe_int(df["product_count"])
    df["total_revenue_gbp"] = _safe_float(df["total_revenue_gbp"])
    for col in ["signup_date","kyc_submission_date","kyc_completion_date",
                "activation_date","first_transaction_date","premium_upgrade_date",
                "last_activity_date","churn_date"]:
        if col in df.columns:
            df[col] = _to_date(df[col])

    # 2. Required NOT NULL checks (BR-013)
    for col in ["customer_id","customer_uuid","signup_date","kyc_status",
                "lifecycle_stage","age_group","gender"]:
        df = _reject(df, df[col].isna(), f"null_{col}", rejects)

    # 3. Enum validation
    invalid_kyc = ~df["kyc_status"].isin(VALID_KYC_STATUS)
    ctx.record_dq(invalid_kyc.sum() == 0, "transform")
    df = _reject(df, invalid_kyc, "invalid_kyc_status", rejects)

    invalid_stage = ~df["lifecycle_stage"].isin(VALID_LIFECYCLE_STAGES)
    ctx.record_dq(invalid_stage.sum() == 0, "transform")
    df = _reject(df, invalid_stage, "invalid_lifecycle_stage", rejects)

    # 4. BR-001: date ordering
    has_all = df["activation_date"].notna() & df["kyc_completion_date"].notna()
    ordering_ok = ~(
        has_all &
        (df["activation_date"] < df["kyc_completion_date"])
    )
    bad_order = has_all & (df["activation_date"] < df["kyc_completion_date"])
    ctx.record_dq(bad_order.sum() == 0, "transform")
    if bad_order.sum():
        ctx.warn(f"BR-001: {bad_order.sum()} customers with activation < kyc_completion — correcting")
        df.loc[bad_order, "activation_date"] = df.loc[bad_order, "kyc_completion_date"]

    # 5. BR-008: activation only for approved
    bad_activation = df["activation_date"].notna() & (df["kyc_status"] != "approved")
    ctx.record_dq(bad_activation.sum() == 0, "transform")
    df = _reject(df, bad_activation, "BR008_activated_without_kyc", rejects)

    # 6. Deduplication
    dupes = df.duplicated("customer_id", keep="first")
    if dupes.sum():
        ctx.warn(f"dim_customer: {dupes.sum()} duplicate customer_ids removed")
    df = df[~dupes].copy()

    # 7. Feature engineering — surrogate FKs
    df["country_id"]       = df["country_code"].map(COUNTRY_MAP)
    df["channel_id"]       = df["channel_code"].map(CHANNEL_MAP)
    df["signup_date_key"]  = df["signup_date"].apply(_date_to_key)

    # Reject unresolvable FKs
    df = _reject(df, df["country_id"].isna(),   "unresolved_country_fk",  rejects)
    df = _reject(df, df["channel_id"].isna(),   "unresolved_channel_fk",  rejects)
    df = _reject(df, df["signup_date_key"].isna(),"null_signup_date_key",  rejects)

    # 8. Default fills for nullable warehouse columns
    df["city"]     = df.get("city",     pd.Series(dtype=str)).fillna("")
    df["clv_band"] = df.get("clv_band", pd.Series(dtype=str)).fillna("Bronze")
    df["churn_risk_score"] = _safe_float(df.get("churn_risk_score",
                                                  pd.Series(dtype=float)))

    ctx.record_dq(True, "transform")
    n_out = len(df)
    ctx.log_audit("dim_customer", "transform", n_out,
                  f"rejected={n_in - n_out}")
    logger.info(f"  dim_customer:          {n_in:>7,} → {n_out:>7,} "
                f"(rejected {n_in - n_out})")
    return df


def transform_fact_customer_journey(df: pd.DataFrame, customer_ids: set,
                                     ctx: ETLContext,
                                     rejects: List[Dict]) -> pd.DataFrame:
    n_in = len(df)
    for col in ["signup_date","kyc_submission_date","kyc_completion_date",
                "activation_date","first_transaction_date","premium_upgrade_date","churn_date"]:
        if col in df.columns:
            df[col] = _to_date(df[col])

    # Referential integrity: customer must exist in dim_customer
    df = _reject(df, ~df["customer_id"].isin(customer_ids),
                 "fk_customer_not_in_dim", rejects)

    # Dedup (UNIQUE constraint on customer_id)
    df = df.drop_duplicates("customer_id", keep="first")

    # Surrogate keys
    df["country_id"]      = df["country_code"].map(COUNTRY_MAP)
    df["channel_id"]      = df["channel_code"].map(CHANNEL_MAP)
    df["signup_date_key"] = df["signup_date"].apply(_date_to_key)
    df = _reject(df, df["country_id"].isna(),    "unresolved_country_fk", rejects)
    df = _reject(df, df["channel_id"].isna(),    "unresolved_channel_fk", rejects)
    df = _reject(df, df["signup_date_key"].isna(),"null_signup_date_key", rejects)

    # Days-to fields: coerce to int, fill nulls with -1 (sentinel for "not reached")
    for col in ["days_to_kyc_submission","days_to_kyc_completion",
                "days_to_activation","days_to_premium"]:
        if col in df.columns:
            df[col] = _safe_int(df[col], fill=-1)

    n_out = len(df)
    ctx.log_audit("fact_customer_journey", "transform", n_out, f"rejected={n_in-n_out}")
    logger.info(f"  fact_customer_journey: {n_in:>7,} → {n_out:>7,} "
                f"(rejected {n_in-n_out})")
    return df


def transform_fact_transactions(df: pd.DataFrame, customer_ids: set,
                                  ctx: ETLContext,
                                  rejects: List[Dict]) -> pd.DataFrame:
    n_in = len(df)
    df["transaction_date"] = _to_date(df["transaction_date"])

    # Referential integrity
    df = _reject(df, ~df["customer_id"].isin(customer_ids),
                 "fk_customer_not_in_dim", rejects)

    # BR-003: non-negative amounts
    df = _reject(df, df["amount_local"] <= 0, "BR003_zero_amount", rejects)
    df = _reject(df, df["fee_amount_local"] < 0, "BR003_negative_fee", rejects)

    # Status enum
    df = _reject(df, ~df["status"].isin(VALID_TXN_STATUS),
                 "invalid_txn_status", rejects)
    ctx.record_dq(True, "transform")

    # Surrogate keys
    df["product_id"]            = df["product_code"].map(PRODUCT_MAP)
    df["country_id"]            = df["country_code"].map(COUNTRY_MAP)
    df["transaction_date_key"]  = df["transaction_date"].apply(_date_to_key)
    df = _reject(df, df["product_id"].isna(),           "unresolved_product_fk",  rejects)
    df = _reject(df, df["country_id"].isna(),           "unresolved_country_fk",  rejects)
    df = _reject(df, df["transaction_date_key"].isna(), "null_txn_date_key",       rejects)

    # Feature: transaction_timestamp (midday on transaction_date — no sub-day data)
    df["transaction_timestamp"] = pd.to_datetime(df["transaction_date"].astype(str)) + \
                                   pd.Timedelta(hours=12)

    # Null fill: failure_reason
    df["failure_reason"]  = df["failure_reason"].fillna("")
    df["merchant_name"]   = df.get("merchant_name",   pd.Series(dtype=str)).fillna("")
    df["merchant_category"] = df.get("merchant_category", pd.Series(dtype=str)).fillna("")
    df["customer_segment"] = df.get("customer_segment", pd.Series(dtype=str)).fillna("unknown")

    n_out = len(df)
    ctx.log_audit("fact_transactions", "transform", n_out, f"rejected={n_in-n_out}")
    logger.info(f"  fact_transactions:     {n_in:>7,} → {n_out:>7,} "
                f"(rejected {n_in-n_out})")
    return df


def transform_fact_product_events(df: pd.DataFrame, customer_ids: set,
                                    ctx: ETLContext,
                                    rejects: List[Dict]) -> pd.DataFrame:
    n_in = len(df)
    df["event_date"] = _to_date(df["event_date"])
    df = _reject(df, ~df["customer_id"].isin(customer_ids),
                 "fk_customer_not_in_dim", rejects)

    df["product_id"]     = df["product_code"].map(PRODUCT_MAP)
    df["country_id"]     = df["country_code"].map(COUNTRY_MAP)
    df["event_date_key"] = df["event_date"].apply(_date_to_key)
    df = _reject(df, df["product_id"].isna(),     "unresolved_product_fk", rejects)
    df = _reject(df, df["country_id"].isna(),     "unresolved_country_fk", rejects)
    df = _reject(df, df["event_date_key"].isna(), "null_event_date_key",   rejects)

    df["event_timestamp"] = pd.to_datetime(df["event_date"].astype(str)) + \
                             pd.Timedelta(hours=10)
    df["device_type"] = df["device_type"].fillna("Unknown")

    # Serialise event_properties dict to JSON string for JSONB storage
    def _safe_json(x):
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return "{}"
        try:
            return json.dumps(x) if isinstance(x, dict) else str(x)
        except Exception:
            return "{}"
    df["event_properties"] = df["event_properties"].apply(_safe_json)

    n_out = len(df)
    ctx.log_audit("fact_product_events", "transform", n_out, f"rejected={n_in-n_out}")
    logger.info(f"  fact_product_events:   {n_in:>7,} → {n_out:>7,} "
                f"(rejected {n_in-n_out})")
    return df


def transform_fact_revenue(df: pd.DataFrame, customer_ids: set,
                             ctx: ETLContext,
                             rejects: List[Dict]) -> pd.DataFrame:
    n_in = len(df)
    date_col = "transaction_date" if "transaction_date" in df.columns else "revenue_date"
    df["revenue_date"] = _to_date(df[date_col])
    df = _reject(df, ~df["customer_id"].isin(customer_ids),
                 "fk_customer_not_in_dim", rejects)

    df["product_id"]       = df["product_code"].map(PRODUCT_MAP)
    df["country_id"]       = df["country_code"].map(COUNTRY_MAP)
    df["revenue_date_key"] = df["revenue_date"].apply(_date_to_key)
    df = _reject(df, df["product_id"].isna(),       "unresolved_product_fk", rejects)
    df = _reject(df, df["country_id"].isna(),       "unresolved_country_fk", rejects)
    df = _reject(df, df["revenue_date_key"].isna(), "null_revenue_date_key", rejects)

    # BR-004: net_revenue = gross - refunds
    df["gross_revenue_gbp"] = _safe_float(df["gross_revenue_gbp"])
    df["refunds_gbp"]       = _safe_float(df.get("refunds_gbp", pd.Series(0.0)))
    df["net_revenue_gbp"]   = (df["gross_revenue_gbp"] - df["refunds_gbp"]).round(4)

    # Free-transfer revenue must be zero (BR-004)
    free_with_revenue = (df["revenue_type"] == "transfer_free") & (df["net_revenue_gbp"] > 0)
    if free_with_revenue.sum():
        ctx.warn(f"fact_revenue: {free_with_revenue.sum()} free-transfer rows with revenue — zeroing")
        df.loc[free_with_revenue, "net_revenue_gbp"] = 0.0

    # Add premium flag
    df["is_premium_revenue"] = df["revenue_type"] == "subscription"

    # Deduplicate on the unique constraint grain
    grain = ["customer_id","product_id","revenue_date_key","revenue_type"]
    before = len(df)
    df = df.sort_values("net_revenue_gbp", ascending=False).drop_duplicates(grain, keep="first")
    if len(df) < before:
        ctx.warn(f"fact_revenue: removed {before-len(df)} duplicate grain rows")

    n_out = len(df)
    ctx.log_audit("fact_revenue", "transform", n_out, f"rejected={n_in-n_out}")
    logger.info(f"  fact_revenue:          {n_in:>7,} → {n_out:>7,} "
                f"(rejected {n_in-n_out})")
    return df


def transform_fact_marketing(df: pd.DataFrame, customer_ids: set,
                               ctx: ETLContext,
                               rejects: List[Dict]) -> pd.DataFrame:
    n_in = len(df)
    df["touchpoint_date"] = _to_date(df["touchpoint_date"])
    if "conversion_date" in df.columns:
        df["conversion_date"] = _to_date(df["conversion_date"])

    df = _reject(df, ~df["customer_id"].isin(customer_ids),
                 "fk_customer_not_in_dim", rejects)
    df = df.drop_duplicates("customer_id", keep="first")

    df["channel_id"]          = df["channel_code"].map(CHANNEL_MAP)
    df["country_id"]          = df["country_code"].map(COUNTRY_MAP)
    df["touchpoint_date_key"] = df["touchpoint_date"].apply(_date_to_key)
    df = _reject(df, df["channel_id"].isna(),           "unresolved_channel_fk", rejects)
    df = _reject(df, df["country_id"].isna(),           "unresolved_country_fk", rejects)
    df = _reject(df, df["touchpoint_date_key"].isna(),  "null_touchpoint_date_key", rejects)

    df["acquisition_cost_gbp"] = _safe_float(df["acquisition_cost_gbp"])
    df["days_to_conversion"]   = _safe_int(df.get("days_to_conversion", pd.Series(dtype=float)), fill=-1)
    df["campaign_id"]          = df.get("campaign_id",   pd.Series(dtype=str)).fillna("")
    df["campaign_name"]        = df.get("campaign_name", pd.Series(dtype=str)).fillna("")

    n_out = len(df)
    ctx.log_audit("fact_marketing", "transform", n_out, f"rejected={n_in-n_out}")
    logger.info(f"  fact_marketing:        {n_in:>7,} → {n_out:>7,} "
                f"(rejected {n_in-n_out})")
    return df


def transform_fact_support(df: pd.DataFrame, customer_ids: set,
                             ctx: ETLContext,
                             rejects: List[Dict]) -> pd.DataFrame:
    n_in = len(df)
    df["created_date"]  = _to_date(df["created_date"])
    if "resolved_date" in df.columns:
        df["resolved_date"] = _to_date(df["resolved_date"])

    df = _reject(df, ~df["customer_id"].isin(customer_ids),
                 "fk_customer_not_in_dim", rejects)
    df = _reject(df, ~df["priority"].isin(VALID_PRIORITIES), "invalid_priority", rejects)

    df["country_id"]        = df["country_code"].map(COUNTRY_MAP)
    df["created_date_key"]  = df["created_date"].apply(_date_to_key)
    df = _reject(df, df["country_id"].isna(),       "unresolved_country_fk", rejects)
    df = _reject(df, df["created_date_key"].isna(), "null_created_date_key", rejects)

    df["satisfaction_score"] = pd.to_numeric(
        df.get("satisfaction_score"), errors="coerce")   # keep nullable
    df["first_response_time_hrs"] = _safe_float(
        df.get("first_response_time_hrs", pd.Series(0.0)))

    # Feature: created_at timestamp
    df["created_at"] = pd.to_datetime(df["created_date"].astype(str)) + \
                        pd.Timedelta(hours=9)
    df["resolved_at"] = df.apply(
        lambda r: (pd.Timestamp(str(r["resolved_date"])) + pd.Timedelta(hours=9))
                   if pd.notna(r.get("resolved_date")) else pd.NaT, axis=1)

    # Ensure Timestamp columns with NaT are converted to None-safe objects
    # psycopg2 cannot handle pandas NaT directly
    for ts_col in ["created_at", "resolved_at", "first_response_at"]:
        if ts_col in df.columns:
            df[ts_col] = df[ts_col].apply(
                lambda x: x if pd.notna(x) else None
            )

    n_out = len(df)
    ctx.log_audit("fact_support", "transform", n_out, f"rejected={n_in-n_out}")
    logger.info(f"  fact_support:          {n_in:>7,} → {n_out:>7,} "
                f"(rejected {n_in-n_out})")
    return df


def transform_fact_kyc_events(df: pd.DataFrame, customer_ids: set,
                                ctx: ETLContext,
                                rejects: List[Dict]) -> pd.DataFrame:
    n_in = len(df)
    df["submission_date"] = _to_date(df["submission_date"])
    if "completion_date" in df.columns:
        df["completion_date"] = _to_date(df["completion_date"])

    df = _reject(df, ~df["customer_id"].isin(customer_ids),
                 "fk_customer_not_in_dim", rejects)
    df = _reject(df, df["submission_date"].isna(), "null_submission_date", rejects)

    df["country_id"]          = df["country_code"].map(COUNTRY_MAP)
    df["submission_date_key"] = df["submission_date"].apply(_date_to_key)
    df = _reject(df, df["country_id"].isna(),          "unresolved_country_fk",   rejects)
    df = _reject(df, df["submission_date_key"].isna(), "null_submission_date_key", rejects)

    df["processing_time_hours"] = _safe_float(
        df.get("processing_time_hours", pd.Series(dtype=float)))
    df["rejection_reason"]  = df.get("rejection_reason", pd.Series(dtype=str)).fillna("")
    df["submission_timestamp"] = pd.to_datetime(df["submission_date"].astype(str)) + \
                                  pd.Timedelta(hours=9)

    # Ensure Timestamp columns with NaT are None-safe for psycopg2
    for ts_col in ["submission_timestamp", "completion_timestamp"]:
        if ts_col in df.columns:
            df[ts_col] = df[ts_col].apply(
                lambda x: x if pd.notna(x) else None
            )

    n_out = len(df)
    ctx.log_audit("fact_kyc_events", "transform", n_out, f"rejected={n_in-n_out}")
    logger.info(f"  fact_kyc_events:       {n_in:>7,} → {n_out:>7,} "
                f"(rejected {n_in-n_out})")
    return df


# ── Orchestrator ───────────────────────────────────────────────────────────────

def transform_all(raw: Dict[str, pd.DataFrame],
                  ctx: ETLContext) -> Tuple[Dict[str, pd.DataFrame], List[Dict]]:
    """
    Apply all per-table transformations in dependency order.
    dim_customer must be first — all facts FK into it.
    Returns (transformed_tables, reject_log).
    """
    stage = ctx.begin_stage("transform")
    rejects: List[Dict] = []
    result:  Dict[str, pd.DataFrame] = {}

    logger.info("[TRANSFORM] Starting transformation pipeline")

    # ── 1. Dimensions first ───────────────────────────────────────────────────
    if "dim_customer" in raw:
        result["dim_customer"] = transform_dim_customer(raw["dim_customer"].copy(),
                                                         ctx, rejects)

    # Valid customer IDs after transformation (used for FK checks)
    valid_customers: set = set(result["dim_customer"]["customer_id"].tolist()) \
        if "dim_customer" in result else set()

    # ── 2. Facts (in load-dependency order) ───────────────────────────────────
    if "fact_customer_journey" in raw:
        result["fact_customer_journey"] = transform_fact_customer_journey(
            raw["fact_customer_journey"].copy(), valid_customers, ctx, rejects)

    if "fact_transactions" in raw:
        result["fact_transactions"] = transform_fact_transactions(
            raw["fact_transactions"].copy(), valid_customers, ctx, rejects)

    if "fact_product_events" in raw:
        result["fact_product_events"] = transform_fact_product_events(
            raw["fact_product_events"].copy(), valid_customers, ctx, rejects)

    if "fact_revenue" in raw:
        result["fact_revenue"] = transform_fact_revenue(
            raw["fact_revenue"].copy(), valid_customers, ctx, rejects)

    if "fact_marketing" in raw:
        result["fact_marketing"] = transform_fact_marketing(
            raw["fact_marketing"].copy(), valid_customers, ctx, rejects)

    if "fact_support" in raw:
        result["fact_support"] = transform_fact_support(
            raw["fact_support"].copy(), valid_customers, ctx, rejects)

    if "fact_kyc_events" in raw:
        result["fact_kyc_events"] = transform_fact_kyc_events(
            raw["fact_kyc_events"].copy(), valid_customers, ctx, rejects)

    # ── Totals ────────────────────────────────────────────────────────────────
    total_in  = sum(len(raw[t]) for t in raw)
    total_out = sum(len(result[t]) for t in result)

    stage.rows_in      = total_in
    stage.rows_out     = total_out
    stage.rows_rejected = len(rejects)
    ctx.total_transformed = total_out
    ctx.total_rejected    = len(rejects)
    ctx.end_stage("transform")

    logger.success(f"[TRANSFORM] Complete: {total_out:,} rows clean, "
                   f"{len(rejects):,} rejected, {stage.duration_s}s")
    return result, rejects
