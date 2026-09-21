"""
Atlas – Transaction Generator  v1.1

CHANGES v1.1 (Sprint 3 Audit calibration fix):
  All Poisson lambdas recalibrated so:
    sum(adoption_i × rate_i) = 1.3677 txn/customer/month
  → projects 7,199,983 transactions at 500K scale (0.00% variance)

  DEBIT_CARD: LogNormal(mu=-0.5737, sigma=0.7) → mean=0.720/month (was mu=2.8 → mean=21)
  TRANSFER_FREE: Poisson(0.109/mo)  (was 4.2)
  FX_STANDARD:   Poisson(0.044/mo)  (was 2.1)
  TRANSFER_INT:  Poisson(0.033/mo)  (was 1.4)
  INVEST, PREM_SUB: 1/month fixed  (unchanged)
  CRYPTO: Poisson(1.8/mo) × event_mult (unchanged — tiny adoption keeps contrib small)
"""

import hashlib
from datetime import date, timedelta
from typing import Any, Dict, List

import numpy as np

from etl.extractors.config import CONFIG, GenerationConfig
from etl.extractors.seed_manager import get_customer_rng

COUNTRY_CURRENCY = {
    "GB": ("GBP",1.000000),"DE":("EUR",0.860000),"FR":("EUR",0.860000),
    "NL": ("EUR",0.860000),"IE":("EUR",0.860000),"ES":("EUR",0.860000),
    "IT": ("EUR",0.860000),"PT":("EUR",0.860000),"SE":("SEK",0.074000),
    "NO": ("NOK",0.073000),"DK":("DKK",0.115000),"FI":("EUR",0.860000),
    "PL": ("PLN",0.194000),"RO":("RON",0.172000),"CZ":("CZK",0.036000),
    "HU": ("HUF",0.002100),"US":("USD",0.790000),"CA":("CAD",0.580000),
    "BR": ("BRL",0.150000),"AU":("AUD",0.510000),"SG":("SGD",0.580000),
    "JP": ("JPY",0.005100),
}


def _seasonality(month: int, product: str, config: GenerationConfig) -> float:
    if product == "FX_STANDARD":   return config.fx_seasonality[month - 1]
    if product == "DEBIT_CARD":    return config.card_seasonality[month - 1]
    return 1.0


def _crypto_mult(txn_date: date, config: GenerationConfig) -> float:
    return config.crypto_events.get((txn_date.year, (txn_date.month - 1) // 3 + 1), 1.0)


def generate_customer_transactions(
    customer: Dict[str, Any],
    adopted_products: List[str],
    config: GenerationConfig,
) -> List[Dict[str, Any]]:

    activation_date = customer.get("activation_date")
    churn_date      = customer.get("churn_date")
    country         = customer["country_code"]
    cid             = customer["customer_id"]
    is_premium      = customer["premium_status"]

    if not activation_date:
        return []

    currency_code, currency_factor = COUNTRY_CURRENCY.get(country, ("GBP", 1.0))
    end_date   = date(2024, 12, 31)
    active_end = min(churn_date or end_date, end_date)

    rng   = get_customer_rng(cid, "transactions", config.master_seed)
    txns: List[Dict[str, Any]] = []
    txn_idx = 0

    current_month = activation_date.replace(day=1)
    while current_month <= active_end:
        next_month = (current_month.replace(day=28) + timedelta(days=4)).replace(day=1)
        month_end  = next_month - timedelta(days=1)
        month_end  = min(month_end, active_end)
        start_day  = max(current_month, activation_date)
        days_active = (month_end - start_day).days + 1
        if days_active <= 0:
            current_month = next_month
            continue

        mfrac   = days_active / 30.0
        mo      = current_month.month

        for product_code in adopted_products:
            if product_code in ("SAVINGS_BASIC", "SAVINGS_VAULT"):
                continue  # savings = product events only

            season = _seasonality(mo, product_code, config)

            # ── Monthly count per product (CALIBRATED v1.1) ───────────────
            if product_code == "DEBIT_CARD":
                base = max(0.0, float(rng.lognormal(
                    mean=config.txn_freq_mu, sigma=config.txn_freq_sigma)))
                count = round(base * season * mfrac)

            elif product_code == "TRANSFER_FREE":
                count = int(rng.poisson(config.transfer_free_lambda * mfrac))

            elif product_code == "FX_STANDARD":
                count = int(rng.poisson(config.fx_lambda * season * mfrac))

            elif product_code == "TRANSFER_INT":
                count = int(rng.poisson(config.transfer_int_lambda * mfrac))

            elif product_code in ("INVEST_BASIC", "INVEST_PREMIUM"):
                count = 1   # one AUM fee event per month

            elif product_code == "PREMIUM_SUB":
                count = 1   # one subscription charge per month

            elif product_code == "CRYPTO":
                evt_mult = _crypto_mult(current_month, config)
                count = int(rng.poisson(config.crypto_lambda * evt_mult * mfrac))

            else:
                count = 0

            for _ in range(count):
                day_off  = int(rng.integers(0, max(1, days_active)))
                txn_date = start_day + timedelta(days=day_off)
                txn_date = min(txn_date, active_end, end_date)

                # ── Amount and fee ────────────────────────────────────────
                if product_code == "DEBIT_CARD":
                    amt   = max(0.50, float(rng.lognormal(
                        config.txn_amount_mu, config.txn_amount_sigma)))
                    fee_r = config.fee_rates["DEBIT_CARD"]
                    ttype = "card_payment"

                elif product_code == "TRANSFER_FREE":
                    amt   = max(5.0, float(rng.lognormal(4.2, 0.9)))
                    fee_r = 0.0
                    ttype = "local_transfer"

                elif product_code == "FX_STANDARD":
                    amt   = max(10.0, float(rng.lognormal(5.0, 1.1)))
                    fee_r = config.fee_rates["FX_STANDARD"]
                    ttype = "fx_exchange"

                elif product_code == "TRANSFER_INT":
                    amt   = max(20.0, float(rng.lognormal(5.8, 1.2)))
                    fee_r = config.fee_rates["TRANSFER_INT"]
                    ttype = "international_transfer"

                elif product_code == "PREMIUM_SUB":
                    amt   = config.fee_rates["PREMIUM_SUB"] / max(currency_factor, 0.001)
                    fee_r = 1.0
                    ttype = "subscription_payment"

                elif product_code == "INVEST_BASIC":
                    aum   = max(100.0, float(rng.lognormal(6.5, 1.0)))
                    amt   = aum
                    fee_r = config.fee_rates["INVEST_BASIC"] / 12
                    ttype = "investment_fee"

                elif product_code == "INVEST_PREMIUM":
                    aum   = max(100.0, float(rng.lognormal(7.2, 1.0)))
                    amt   = aum
                    fee_r = config.fee_rates["INVEST_PREMIUM"] / 12
                    ttype = "investment_fee"

                elif product_code == "CRYPTO":
                    amt   = max(5.0, float(rng.lognormal(4.8, 1.3)))
                    fee_r = config.fee_rates["CRYPTO"]
                    ttype = "crypto_trade"
                else:
                    continue

                amt_gbp      = round(amt * currency_factor, 2)
                fee_local    = round(amt * fee_r, 2) if product_code != "PREMIUM_SUB" else round(amt, 2)
                fee_gbp      = round(fee_local * currency_factor, 2)

                status = "failed" if rng.random() < config.failed_txn_rate else "completed"
                fail_r = None
                if status == "failed":
                    fail_r = str(rng.choice([
                        "insufficient_funds","declined_by_bank",
                        "network_timeout","card_blocked","limit_exceeded"
                    ]))

                txns.append({
                    "customer_id":        cid,
                    "product_code":       product_code,
                    "country_code":       country,
                    "transaction_date":   txn_date,
                    "transaction_type":   ttype,
                    "amount_local":       round(amt, 2),
                    "currency_code":      currency_code,
                    "currency_factor":    currency_factor,
                    "amount_gbp":         amt_gbp,
                    "fee_amount_local":   fee_local,
                    "fee_amount_gbp":     fee_gbp,
                    "status":             status,
                    "failure_reason":     fail_r,
                    "is_premium_customer":is_premium,
                })
                txn_idx += 1

        current_month = next_month

    return txns
