"""
Atlas – Product Event & Fraud Event Generator
Generates fact_product_events including fraud/risk events.
Target: ~11.5M rows total.
"""

import hashlib
from datetime import date, timedelta
from typing import Any, Dict, List

import numpy as np

from etl.extractors.config import CONFIG, GenerationConfig
from etl.extractors.seed_manager import get_customer_rng

# ── Product adoption logic ────────────────────────────────────────────────────

def determine_adopted_products(customer: Dict[str, Any],
                                config: GenerationConfig) -> List[str]:
    """
    Determine which products a customer adopts over their lifetime.
    Respects product dependencies (e.g., INVEST_PREMIUM requires PREMIUM_SUB).
    Returns list of adopted product codes.
    """
    cid = customer["customer_id"]
    age_group = customer.get("age_group", "25-34")
    is_premium = customer["premium_status"]
    income_band = customer.get("income_band", "40k-70k")
    activation_date = customer.get("activation_date")

    if not activation_date:
        return []

    adopt_rng = get_customer_rng(cid, "adoption", config.master_seed)
    adopted = []

    # Core products (available to all activated)
    for code, prob in [
        ("DEBIT_CARD",    config.product_adoption["DEBIT_CARD"]),
        ("TRANSFER_FREE", config.product_adoption["TRANSFER_FREE"]),
        ("SAVINGS_BASIC", config.product_adoption["SAVINGS_BASIC"]),
        ("FX_STANDARD",   config.product_adoption["FX_STANDARD"]),
        ("TRANSFER_INT",  config.product_adoption["TRANSFER_INT"]),
        ("INVEST_BASIC",  config.product_adoption["INVEST_BASIC"] if age_group != "18-24" else 0.10),
    ]:
        if adopt_rng.random() < prob:
            adopted.append(code)

    # SAVINGS_VAULT: only if SAVINGS_BASIC adopted
    if "SAVINGS_BASIC" in adopted:
        if adopt_rng.random() < config.product_adoption["SAVINGS_VAULT"]:
            adopted.append("SAVINGS_VAULT")

    # PREMIUM_SUB
    if is_premium:
        adopted.append("PREMIUM_SUB")

        # Premium-only products
        if adopt_rng.random() < config.product_adoption["INVEST_PREMIUM"]:
            adopted.append("INVEST_PREMIUM")

        # CRYPTO: premium + age 18-44 + (AMENDED) 18% rate
        is_young = age_group in ("18-24", "25-34", "35-44")
        if is_young and adopt_rng.random() < config.product_adoption["CRYPTO"]:
            adopted.append("CRYPTO")

    return adopted


def generate_product_adoption_events(customer: Dict[str, Any],
                                      adopted_products: List[str],
                                      config: GenerationConfig) -> List[Dict[str, Any]]:
    """Generate one-time adoption events for each product the customer adopts."""
    cid = customer["customer_id"]
    activation_date = customer["activation_date"]
    end_date = date(2024, 12, 31)

    if not activation_date:
        return []

    rng = get_customer_rng(cid, "adoption_events", config.master_seed)
    events = []

    event_map = {
        "DEBIT_CARD":     "card_activated",
        "SAVINGS_BASIC":  "savings_opened",
        "SAVINGS_VAULT":  "savings_opened",
        "INVEST_BASIC":   "investment_opened",
        "INVEST_PREMIUM": "investment_opened",
        "PREMIUM_SUB":    "premium_purchased",
        "CRYPTO":         "crypto_activated",
        "FX_STANDARD":    "fx_activated",
        "TRANSFER_INT":   "transfer_activated",
        "TRANSFER_FREE":  "transfer_activated",
    }

    for product_code in adopted_products:
        event_type = event_map.get(product_code, "product_activated")
        # Log-normal days to adoption from activation
        days = max(0, round(rng.lognormal(mean=2.5, sigma=0.8)))
        event_date = activation_date + timedelta(days=days)
        if event_date > end_date:
            continue

        events.append({
            "customer_id":   cid,
            "product_code":  product_code,
            "country_code":  customer["country_code"],
            "event_date":    event_date,
            "event_type":    event_type,
            "event_properties": {"adoption_day": days, "source": "onboarding"},
            "device_type":   customer.get("device_type", "iOS"),
        })

    return events


def generate_recurring_product_events(customer: Dict[str, Any],
                                       adopted_products: List[str],
                                       config: GenerationConfig) -> List[Dict[str, Any]]:
    """Generate ongoing usage events (logins, feature views, etc.) post-adoption."""
    cid = customer["customer_id"]
    activation_date = customer["activation_date"]
    churn_date = customer.get("churn_date")
    end_date = date(2024, 12, 31)
    active_end = min(churn_date or end_date, end_date)

    if not activation_date or not adopted_products:
        return []

    rng = get_customer_rng(cid, "recurring_events", config.master_seed)
    events = []

    # Monthly logins / app interactions
    current = activation_date.replace(day=1)
    while current <= active_end:
        month_end = (current.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        month_end = min(month_end, active_end)

        # LogNormal(0.456, 0.7) → mean=2.0 logins/month.  Calibrated so that
        # 351,600 activated × 15 avg months × 2.0 = 10.5M login events,
        # plus ~1M adoption+fraud events = 11.5M total (blueprint target).
        # LogNormal(0.456, 0.7) → mean=2.0 logins/month, no floor clip.
        # Allows some months with 0 logins (realistic). Removing max(1,...)
        # corrects an upward bias of ~0.5 logins/month from clipping.
        login_count = round(rng.lognormal(mean=0.456, sigma=0.7))
        for _ in range(login_count):
            days_in = int(rng.integers(0, max(1, (month_end - current).days + 1)))
            event_date = current + timedelta(days=days_in)
            if event_date > active_end:
                continue
            events.append({
                "customer_id":  cid,
                "product_code": "DEBIT_CARD" if "DEBIT_CARD" in adopted_products else adopted_products[0],
                "country_code": customer["country_code"],
                "event_date":   event_date,
                "event_type":   "app_login",
                "event_properties": {"session_minutes": round(float(rng.exponential(8)), 1)},
                "device_type":  customer.get("device_type", "iOS"),
            })

        current = (current.replace(day=28) + timedelta(days=4)).replace(day=1)

    return events


def generate_fraud_events(transactions: List[Dict[str, Any]],
                           customer: Dict[str, Any],
                           config: GenerationConfig) -> List[Dict[str, Any]]:
    """
    Generate fraud/risk events referencing completed transactions.
    fraud_flagged → fraud_cleared (78%) or unresolved (22%)
    suspicious_transfer on TRANSFER_INT
    chargeback on DEBIT_CARD
    """
    cid = customer["customer_id"]
    fraud_rng = get_customer_rng(cid, "fraud", config.master_seed)
    events = []

    completed = [t for t in transactions if t["status"] == "completed"]

    for i, txn in enumerate(completed):
        product = txn["product_code"]
        txn_date = txn["transaction_date"]
        amount_gbp = txn["amount_gbp"]

        # ── fraud_flagged ──────────────────────────────────────────────────
        if fraud_rng.random() < config.fraud_flag_rate:
            flag_reasons = ["unusual_amount", "new_device", "foreign_country", "velocity_check"]
            risk_score = round(float(fraud_rng.uniform(45, 95)), 1)
            flag_id = f"flag_{cid}_{i}"

            events.append({
                "customer_id":   cid,
                "product_code":  product,
                "country_code":  txn["country_code"],
                "event_date":    txn_date,
                "event_type":    "fraud_flagged",
                "event_properties": {
                    "flag_id":      flag_id,
                    "flag_reason":  str(fraud_rng.choice(flag_reasons)),
                    "amount_gbp":   amount_gbp,
                    "risk_score":   risk_score,
                },
                "device_type":   customer.get("device_type"),
            })

            # ── fraud_cleared ──────────────────────────────────────────────
            if fraud_rng.random() < config.fraud_cleared_rate:
                review_hours = max(0.1, float(fraud_rng.lognormal(mean=1.8, sigma=0.9)))
                cleared_date = txn_date + timedelta(hours=review_hours)
                if isinstance(cleared_date, float):
                    cleared_date = txn_date
                events.append({
                    "customer_id":   cid,
                    "product_code":  product,
                    "country_code":  txn["country_code"],
                    "event_date":    txn_date + timedelta(days=max(0, round(review_hours / 24))),
                    "event_type":    "fraud_cleared",
                    "event_properties": {
                        "flag_id":         flag_id,
                        "resolution_type": str(fraud_rng.choice(["auto_cleared", "manual_review_cleared"])),
                        "review_hours":    round(review_hours, 2),
                    },
                    "device_type":   customer.get("device_type"),
                })

        # ── suspicious_transfer ────────────────────────────────────────────
        if product == "TRANSFER_INT" and fraud_rng.random() < config.suspicious_transfer_rate:
            aml_score = round(float(fraud_rng.uniform(50, 90)), 1)
            events.append({
                "customer_id":   cid,
                "product_code":  product,
                "country_code":  txn["country_code"],
                "event_date":    txn_date,
                "event_type":    "suspicious_transfer",
                "event_properties": {
                    "flag_reason":    str(fraud_rng.choice(
                        ["velocity_breach", "high_risk_corridor", "amount_threshold"])),
                    "transfer_amount_gbp": amount_gbp,
                    "aml_score":     aml_score,
                },
                "device_type": customer.get("device_type"),
            })

        # ── chargeback ─────────────────────────────────────────────────────
        if product == "DEBIT_CARD" and fraud_rng.random() < config.chargeback_rate:
            days_after = int(fraud_rng.integers(1, 46))
            cb_date = txn_date + timedelta(days=days_after)
            if cb_date <= date(2024, 12, 31):
                outcomes = ["approved", "declined", "pending"]
                events.append({
                    "customer_id":   cid,
                    "product_code":  product,
                    "country_code":  txn["country_code"],
                    "event_date":    cb_date,
                    "event_type":    "chargeback",
                    "event_properties": {
                        "dispute_reason": str(fraud_rng.choice([
                            "unauthorized", "item_not_received",
                            "item_not_as_described", "duplicate"
                        ])),
                        "original_amount_gbp": amount_gbp,
                        "chargeback_fee_gbp":  15.00,
                        "outcome": str(fraud_rng.choice(outcomes, p=[0.65, 0.25, 0.10])),
                    },
                    "device_type": customer.get("device_type"),
                })

    return events
