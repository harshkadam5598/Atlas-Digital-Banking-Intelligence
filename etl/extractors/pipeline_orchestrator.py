"""
Atlas – Sprint 3 Data Generation Pipeline Orchestrator  v1.1
Coordinates all generators in dependency order with checkpointing.

Usage:
    python -m etl.extractors.pipeline_orchestrator              # full 500K
    python -m etl.extractors.pipeline_orchestrator --sample 2000
    python -m etl.extractors.pipeline_orchestrator --force
"""

import argparse
import json
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from loguru import logger
from tqdm import tqdm

from etl.extractors.config import CONFIG, GenerationConfig
from etl.extractors.customer_generator import generate_customers
from etl.extractors.product_event_generator import (
    determine_adopted_products, generate_fraud_events,
    generate_product_adoption_events, generate_recurring_product_events,
)
from etl.extractors.support_kyc_generator import generate_kyc_events, generate_support_tickets
from etl.extractors.transaction_generator import generate_customer_transactions
from etl.extractors.validator import DataValidator
from etl.extractors.seed_manager import get_customer_rng as _grng

CHECKPOINT_DIR = Path("data/raw/.checkpoints")
RAW_DIR        = Path("data/raw")

CHANNEL_CAC = {
    "ORGANIC_SEARCH":0.22*8.50,"REFERRAL":0.18*12.00,"GOOGLE_ADS":0.20*28.00,
    "SOCIAL_META":0.16*35.00,"SOCIAL_TIKTOK":0.10*42.00,"INFLUENCER":0.06*55.00,
    "EMAIL":0.05*18.00,"DIRECT":0.03*5.00,
}
CHANNEL_CAC_BY_CODE = {
    "ORGANIC_SEARCH":8.50,"REFERRAL":12.00,"GOOGLE_ADS":28.00,
    "SOCIAL_META":35.00,"SOCIAL_TIKTOK":42.00,"INFLUENCER":55.00,
    "EMAIL":18.00,"DIRECT":5.00,
}


def _cp(stage: int) -> Path:
    return CHECKPOINT_DIR / f"stage_{stage:02d}.json"

def _write_cp(stage: int, rows: int, table: str):
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    _cp(stage).write_text(json.dumps({
        "stage":stage,"table":table,"rows":rows,
        "completed_at":datetime.utcnow().isoformat()
    }))

def _cp_exists(stage: int) -> bool:
    return _cp(stage).exists()

def _flush(records: List[Dict], path: Path):
    if not records:
        return
    new_df = pd.DataFrame(records)
    if path.exists():
        combined = pd.concat([pd.read_parquet(path), new_df], ignore_index=True)
    else:
        combined = new_df
    combined.to_parquet(path, index=False)


def run_pipeline(config: GenerationConfig = CONFIG,
                  sample_size: Optional[int] = None,
                  force: bool = False) -> Dict[str, pd.DataFrame]:

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    if sample_size:
        import dataclasses
        d = dataclasses.asdict(config)
        d["total_customers"] = sample_size
        config = GenerationConfig(**d)
        logger.warning(f"SAMPLE MODE: {sample_size:,} customers")

    logger.info("=" * 60)
    logger.info(f"Atlas Sprint 3 Pipeline v1.1  |  seed={config.master_seed}")
    logger.info(f"Target: {config.total_customers:,} customers")
    logger.info("=" * 60)

    results: Dict[str, pd.DataFrame] = {}

    # Stage 1 — dim_customer
    if not _cp_exists(1) or force:
        logger.info("[Stage 1] Generating dim_customer v1.1...")
        customers_df = generate_customers(config, str(RAW_DIR))
        results["dim_customer"] = customers_df
        _write_cp(1, len(customers_df), "dim_customer")
    else:
        customers_df = pd.read_parquet(RAW_DIR/"dim_customer.parquet")
        results["dim_customer"] = customers_df
        logger.info(f"[Stage 1] Loaded dim_customer: {len(customers_df):,}")

    activated_df = customers_df[
        customers_df["lifecycle_stage"].isin(["activated","churned"])
    ].copy()
    logger.info(f"  Activated for downstream gen: {len(activated_df):,}")

    # Stage 2 — fact_kyc_events
    if not _cp_exists(2) or force:
        logger.info("[Stage 2] Generating fact_kyc_events...")
        kyc_rows = []
        for _, c in tqdm(customers_df.iterrows(), total=len(customers_df), desc="KYC events"):
            kyc_rows.extend(generate_kyc_events(c.to_dict(), config))
        kyc_df = pd.DataFrame(kyc_rows)
        kyc_df.to_parquet(RAW_DIR/"fact_kyc_events.parquet", index=False)
        results["fact_kyc_events"] = kyc_df
        _write_cp(2, len(kyc_df), "fact_kyc_events")
        logger.success(f"  fact_kyc_events: {len(kyc_df):,}")
    else:
        results["fact_kyc_events"] = pd.read_parquet(RAW_DIR/"fact_kyc_events.parquet")

    # Stage 3 — fact_marketing
    if not _cp_exists(3) or force:
        logger.info("[Stage 3] Generating fact_marketing...")
        mkt_rows = []
        for _, c in customers_df.iterrows():
            cid = c["customer_id"]
            rng = _grng(cid, "marketing", config.master_seed)
            base_cac = CHANNEL_CAC_BY_CODE.get(c["channel_code"], 20.0)
            cost = round(float(base_cac * rng.lognormal(0, 0.3)), 2)
            is_conv = c["lifecycle_stage"] in ("activated","churned")
            conv_date = c["activation_date"] if is_conv else None
            days = (int((pd.Timestamp(conv_date) - pd.Timestamp(c["signup_date"])).days)
                    if is_conv and conv_date and c["signup_date"] else None)
            mkt_rows.append({
                "customer_id":         cid,
                "country_code":        c["country_code"],
                "channel_code":        c["channel_code"],
                "touchpoint_date":     c["signup_date"],
                "acquisition_cost_gbp":cost,
                "is_converted":        is_conv,
                "conversion_date":     conv_date,
                "days_to_conversion":  days,
            })
        mkt_df = pd.DataFrame(mkt_rows)
        mkt_df.to_parquet(RAW_DIR/"fact_marketing.parquet", index=False)
        results["fact_marketing"] = mkt_df
        _write_cp(3, len(mkt_df), "fact_marketing")
        logger.success(f"  fact_marketing: {len(mkt_df):,}")
    else:
        results["fact_marketing"] = pd.read_parquet(RAW_DIR/"fact_marketing.parquet")

    # Stage 4 — transactions + events + fraud + support
    if not _cp_exists(4) or force:
        logger.info("[Stage 4] Generating transactions, events, fraud, support...")
        all_txns, all_events, all_support = [], [], []
        product_counts: Dict[int, int] = {}
        BATCH = 5_000
        n = len(activated_df)

        for b0 in tqdm(range(0, n, BATCH), desc="Customer batches"):
            for _, c in activated_df.iloc[b0:b0+BATCH].iterrows():
                cd = c.to_dict()
                cid = cd["customer_id"]
                adopted = determine_adopted_products(cd, config)
                product_counts[cid] = len(adopted)

                txns = generate_customer_transactions(cd, adopted, config)
                all_txns.extend(txns)
                all_events.extend(generate_product_adoption_events(cd, adopted, config))
                all_events.extend(generate_recurring_product_events(cd, adopted, config))
                if txns:
                    all_events.extend(generate_fraud_events(txns, cd, config))
                all_support.extend(generate_support_tickets(cd, config))

            if len(all_txns) > 400_000 or b0+BATCH >= n:
                _flush(all_txns,   RAW_DIR/"fact_transactions.parquet")
                _flush(all_events, RAW_DIR/"fact_product_events.parquet")
                all_txns.clear(); all_events.clear()

        if all_support:
            pd.DataFrame(all_support).to_parquet(RAW_DIR/"fact_support.parquet", index=False)

        # Back-fill product count to dim_customer
        customers_df["product_count"] = customers_df["customer_id"].map(product_counts).fillna(0).astype(int)
        customers_df.to_parquet(RAW_DIR/"dim_customer.parquet", index=False)
        results["dim_customer"] = customers_df
        _write_cp(4, 1, "transactions+events+support")

    for fname, key in [
        ("fact_transactions.parquet",    "fact_transactions"),
        ("fact_product_events.parquet",  "fact_product_events"),
        ("fact_support.parquet",         "fact_support"),
    ]:
        p = RAW_DIR/fname
        if p.exists():
            df = pd.read_parquet(p)
            results[key] = df
            logger.info(f"  {key}: {len(df):,}")

    # Stage 5 — fact_revenue
    if not _cp_exists(5) or force:
        logger.info("[Stage 5] Deriving fact_revenue...")
        txn_df = results.get("fact_transactions", pd.DataFrame())
        if len(txn_df):
            completed = txn_df[txn_df["status"] == "completed"].copy()
            rev_df = (completed
                      .groupby(["customer_id","product_code","country_code",
                                "transaction_date","transaction_type"])
                      .agg(gross_revenue_gbp=("fee_amount_gbp","sum"),
                           transaction_count=("fee_amount_gbp","count"))
                      .reset_index())
            rev_map = {
                "card_payment":"card_interchange","subscription_payment":"subscription",
                "fx_exchange":"fx_fee","international_transfer":"transfer_fee",
                "investment_fee":"investment_fee","crypto_trade":"crypto_spread",
                "local_transfer":"transfer_free",
            }
            rev_df["revenue_type"]    = rev_df["transaction_type"].map(rev_map).fillna("other")
            rev_df = rev_df[rev_df["revenue_type"] != "transfer_free"]
            rev_df["refunds_gbp"]     = 0.00
            rev_df["net_revenue_gbp"] = rev_df["gross_revenue_gbp"]
            rev_df.to_parquet(RAW_DIR/"fact_revenue.parquet", index=False)
            results["fact_revenue"] = rev_df
            _write_cp(5, len(rev_df), "fact_revenue")
            logger.success(f"  fact_revenue: {len(rev_df):,}")

    # Stage 6 — fact_customer_journey
    if not _cp_exists(6) or force:
        logger.info("[Stage 6] Building fact_customer_journey...")
        cj = customers_df[[
            "customer_id","country_code","channel_code","signup_date",
            "kyc_submission_date","kyc_completion_date","activation_date",
            "first_transaction_date","premium_upgrade_date","churn_date","kyc_status",
        ]].copy()
        cj["reached_registration"]  = True
        cj["reached_kyc_submitted"] = cj["kyc_submission_date"].notna()
        cj["reached_kyc_approved"]  = cj["kyc_status"] == "approved"
        cj["reached_activation"]    = cj["activation_date"].notna()
        cj["reached_first_deposit"] = cj["first_transaction_date"].notna()
        cj["reached_premium"]       = cj["premium_upgrade_date"].notna()
        cj["is_churned"]            = cj["churn_date"].notna()
        cj["kyc_outcome"]           = cj["kyc_status"]
        for cf, ct, nc in [
            ("signup_date","kyc_submission_date","days_to_kyc_submission"),
            ("kyc_submission_date","kyc_completion_date","days_to_kyc_completion"),
            ("kyc_completion_date","activation_date","days_to_activation"),
            ("activation_date","premium_upgrade_date","days_to_premium"),
        ]:
            mask = cj[cf].notna() & cj[ct].notna()
            cj[nc] = None
            cj.loc[mask, nc] = (pd.to_datetime(cj.loc[mask,ct]) -
                                 pd.to_datetime(cj.loc[mask,cf])).dt.days
        cj.to_parquet(RAW_DIR/"fact_customer_journey.parquet", index=False)
        results["fact_customer_journey"] = cj
        _write_cp(6, len(cj), "fact_customer_journey")
        logger.success(f"  fact_customer_journey: {len(cj):,}")
    else:
        p = RAW_DIR/"fact_customer_journey.parquet"
        if p.exists():
            results["fact_customer_journey"] = pd.read_parquet(p)

    # Load fact_revenue if not in results
    p = RAW_DIR/"fact_revenue.parquet"
    if p.exists() and "fact_revenue" not in results:
        results["fact_revenue"] = pd.read_parquet(p)

    # Validation
    sample_ratio = config.total_customers / CONFIG.total_customers
    logger.info(f"\n[Validation] sample_ratio={sample_ratio:.4f}")

    validator = DataValidator(CONFIG)   # always validate against full-scale config targets
    if "dim_customer" in results and "fact_transactions" in results:
        validator.validate_schema_integrity(results["dim_customer"], results["fact_transactions"])
        validator.validate_business_rules(results["dim_customer"])
        validator.validate_distributions(results["dim_customer"], results["fact_transactions"])

    if "fact_product_events" in results and "fact_transactions" in results:
        validator.validate_fraud_events(results["fact_product_events"], results["fact_transactions"])

    actual_counts = {k: len(v) for k, v in results.items() if v is not None}
    validator.validate_row_counts(actual_counts, sample_ratio=sample_ratio)

    fp1 = validator.write_reproducibility_proof(results, str(RAW_DIR))
    report = validator.write_report(str(RAW_DIR))

    elapsed = time.time() - t0
    passed  = report["summary"]["passed"]
    total   = report["summary"]["total"]
    failed  = report["summary"]["failed"]

    # ── Dataset versioning: snapshot raw/ into versions/ ──────────────────
    try:
        from etl.core.versioning import snapshot_raw_to_version
        label = "sample" if sample_size else "full"
        vdir  = snapshot_raw_to_version(seed=config.master_seed, label=label)
        logger.info(f"Dataset versioned → {vdir.name}")
    except Exception as ve:
        logger.warning(f"Versioning skipped: {ve}")

    logger.info(f"\n{'='*60}")
    logger.info(f"Pipeline complete in {elapsed:.1f}s")
    logger.info(f"Validation: {passed}/{total} passed, {failed} failed")
    logger.info(f"Total rows: {sum(actual_counts.values()):,}")
    logger.info(f"Fingerprint (dim_customer): {fp1[:16]}...")
    logger.info(f"{'='*60}")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=None)
    parser.add_argument("--force",  action="store_true")
    args = parser.parse_args()
    run_pipeline(CONFIG, sample_size=args.sample, force=args.force)
