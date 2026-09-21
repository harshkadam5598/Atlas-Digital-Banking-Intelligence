"""
Atlas – Customer Dimension Generator  v1.1
Generates 500,000 realistic digital banking customers.

CHANGES v1.1 (Sprint 3 Audit fix):
  - Premium formula: replaced tenure sub-rate model with two-stage model
      Stage 1: P(ever premium) = base_rate × country_mult × income_mult  (evaluated once)
      Stage 2: timing → days_to_premium ~ LogNormal(3.5, 1.0)
  - base_rate lifted 0.20 → 0.2144 to offset date-truncation attrition
  - Predicted blended premium rate: 20.0%
"""

import hashlib
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from faker import Faker
from loguru import logger
from tqdm import tqdm

from etl.extractors.config import CONFIG, GenerationConfig
from etl.extractors.seed_manager import derive_seed, get_customer_rng, get_rng

# ── Reference lookup tables ────────────────────────────────────────────────────

COUNTRIES = list(CONFIG.country_weights.keys())
_cw = list(CONFIG.country_weights.values())
COUNTRY_PROBS = [w / sum(_cw) for w in _cw]

CHANNELS = list(CONFIG.channel_weights.keys())
_chw = list(CONFIG.channel_weights.values())
CHANNEL_PROBS = [w / sum(_chw) for w in _chw]

AGE_GROUPS   = ["18-24", "25-34", "35-44", "45-54", "55+"]
AGE_PROBS    = [0.22,    0.31,    0.24,    0.14,    0.09]

GENDERS      = ["Male", "Female", "Non-Binary", "Prefer Not to Say"]
GENDER_PROBS = [0.47,   0.46,    0.04,          0.03]

OCCUPATIONS      = ["Professional","Student","Self-Employed","Skilled Trade",
                     "Manager","Retired","Healthcare","Education","Tech","Other"]
OCCUPATION_PROBS = [0.28, 0.18, 0.14, 0.10, 0.11, 0.06, 0.05, 0.04, 0.03, 0.01]

INCOME_BANDS = ["Under 20k","20k-40k","40k-70k","70k-100k","100k+"]
INCOME_PROBS = [0.15,       0.28,     0.32,     0.16,      0.09]

DEVICE_TYPES = ["iOS","Android","Web"]
DEVICE_PROBS = [0.48, 0.44,    0.08]


# ── Growth curve ───────────────────────────────────────────────────────────────

def build_monthly_registration_targets(config: GenerationConfig) -> List[Tuple[date, int]]:
    rng = get_rng("growth_curve", config.master_seed)
    months = []
    current = date(2022, 1, 1)
    while current <= date(2024, 12, 1):
        months.append(current)
        m = current.month + 1
        y = current.year + (1 if m > 12 else 0)
        current = date(y, m % 12 or 12, 1)

    n = len(months)
    raw_weights = []
    for i, m in enumerate(months):
        yr, mo = m.year, m.month
        if yr == 2022:
            base = 0.08 + 0.005 * i
        elif yr == 2023:
            base = 0.17 + 0.002 * (i - 12)
        else:
            base = 0.06 - 0.003 * (i - 24)

        season = config.acquisition_seasonality[mo - 1]
        noise  = rng.normal(1.0, 0.05)
        raw_weights.append(max(0.001, base * season * noise))

    total_w   = sum(raw_weights)
    targets   = []
    allocated = 0
    for i, (m, w) in enumerate(zip(months, raw_weights)):
        count = config.total_customers - allocated if i == n - 1 else round(config.total_customers * w / total_w)
        allocated += count
        targets.append((m, count))
    return targets


# ── KYC timing ────────────────────────────────────────────────────────────────

def generate_kyc_dates(signup_date: date, kyc_status: str,
                        rng: np.random.Generator) -> Tuple:
    days_to_submit = max(0, round(rng.exponential(1.8)))
    submission = signup_date + timedelta(days=days_to_submit)
    if kyc_status == "pending":
        return submission, None, None
    processing_hours = max(0.5, float(rng.lognormal(mean=2.2, sigma=0.9)))
    completion = submission + timedelta(days=max(1, int(processing_hours / 24)))
    return submission, completion, processing_hours


# ── Premium conversion — TWO-STAGE MODEL (v1.1) ──────────────────────────────
#
# STAGE 1: Does this customer EVER go premium?
#   p = base_rate × country_mult × income_mult
#   Evaluated once per customer, independent of tenure.
#   base_rate = 0.2144 (adjusted for timing truncation to yield 20.0% blended)
#
# STAGE 2: If yes, when?
#   days_to_premium ~ LogNormal(mu=3.5, sigma=1.0)
#   mean ≈ 45 days, 95th pctile ≈ 300 days
#   If premium_date > data end_date: treat as non-converter (date truncation)
#
# FORMULA RATIONALE:
#   The v1.0 formula (base × tenure_rate / 0.20 × mults) had an algebraic
#   cancellation bug: dividing tenure_rate by base_rate eliminated the base,
#   causing the formula to return the raw tenure sub-rate (~0.04) instead of
#   a fraction of 0.20. This produced 2.1% instead of 20%.
#   The two-stage model separates the "if" (Stage 1) from the "when" (Stage 2),
#   making both components independently verifiable and testable.

def calculate_premium_decision(country: str, income_band: str,
                                config: GenerationConfig,
                                rng: np.random.Generator) -> bool:
    """Stage 1: Bernoulli draw — does this customer ever go premium?"""
    country_mult = config.premium_country_mult.get(country, 1.0)
    income_mult  = config.premium_income_mult.get(income_band, 1.0)
    p = min(0.95, config.premium_base_rate * country_mult * income_mult)
    return bool(rng.random() < p)


def generate_premium_timing(activation_date: date, end_date: date,
                             config: GenerationConfig,
                             rng: np.random.Generator) -> date | None:
    """Stage 2: When does the premium conversion happen?"""
    days = max(1, int(rng.lognormal(mean=config.premium_timing_mu,
                                     sigma=config.premium_timing_sigma)))
    upgrade_date = activation_date + timedelta(days=days)
    return upgrade_date if upgrade_date <= end_date else None


# ── Churn ─────────────────────────────────────────────────────────────────────

def generate_churn_date(activation_date: date, end_date: date,
                         rng: np.random.Generator,
                         config: GenerationConfig) -> date | None:
    days_to_churn = rng.weibull(config.churn_weibull_shape) * config.churn_weibull_scale
    churn_date    = activation_date + timedelta(days=int(days_to_churn))
    if churn_date > end_date or (churn_date - activation_date).days < 30:
        return None
    return churn_date


# ── Main generator ────────────────────────────────────────────────────────────

def generate_customers(config: GenerationConfig = CONFIG,
                        output_dir: str = "data/raw") -> pd.DataFrame:
    logger.info(f"Customer generation v1.1 | target={config.total_customers:,} | seed={config.master_seed}")

    fake = Faker(["en_GB", "de_DE", "fr_FR", "pl_PL", "it_IT"])
    Faker.seed(derive_seed(config.master_seed, "faker"))

    global_rng     = get_rng("customers", config.master_seed)
    monthly_targets = build_monthly_registration_targets(config)
    end_date        = date(2024, 12, 31)
    customers: List[Dict[str, Any]] = []
    customer_index = 0

    for month_start, month_count in tqdm(monthly_targets, desc="Generating customers"):
        month_end    = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        days_in_month = (month_end - month_start).days + 1

        for _ in range(month_count):
            rng = get_customer_rng(customer_index, "profile", config.master_seed)

            country     = global_rng.choice(COUNTRIES, p=COUNTRY_PROBS)
            channel     = global_rng.choice(CHANNELS,  p=CHANNEL_PROBS)
            age_group   = rng.choice(AGE_GROUPS,   p=AGE_PROBS)
            gender      = rng.choice(GENDERS,      p=GENDER_PROBS)
            occupation  = rng.choice(OCCUPATIONS,  p=OCCUPATION_PROBS)
            income_band = rng.choice(INCOME_BANDS, p=INCOME_PROBS)
            device      = rng.choice(DEVICE_TYPES, p=DEVICE_PROBS)

            signup_date = month_start + timedelta(days=int(rng.integers(0, days_in_month)))

            kyc_roll = rng.random()
            if kyc_roll < config.kyc_approved_rate:
                kyc_status = "approved"
            elif kyc_roll < config.kyc_approved_rate + config.kyc_rejected_rate:
                kyc_status = "rejected"
            else:
                kyc_status = "pending"

            kyc_submission_date, kyc_completion_date, _ = generate_kyc_dates(
                signup_date, kyc_status,
                get_customer_rng(customer_index, "kyc", config.master_seed)
            )

            activation_date         = None
            first_transaction_date  = None
            premium_upgrade_date    = None
            churn_date              = None
            last_activity_date      = None
            lifecycle_stage         = "registered"
            premium_status          = False

            if kyc_status == "approved" and kyc_completion_date:
                act_rng = get_customer_rng(customer_index, "activation", config.master_seed)
                if act_rng.random() < config.activation_rate:
                    days_to_act  = max(0, round(act_rng.lognormal(mean=2.1, sigma=0.7)))
                    activation_date = kyc_completion_date + timedelta(days=days_to_act)
                    if activation_date <= end_date:
                        first_transaction_date = activation_date
                        lifecycle_stage = "activated"

                        # Churn
                        c_rng = get_customer_rng(customer_index, "churn", config.master_seed)
                        churn_date = generate_churn_date(activation_date, end_date, c_rng, config)
                        if churn_date:
                            lifecycle_stage    = "churned"
                            last_activity_date = churn_date - timedelta(days=90)
                        else:
                            la_rng = get_customer_rng(customer_index, "last_activity", config.master_seed)
                            last_activity_date = end_date - timedelta(days=int(la_rng.integers(0, 60)))

                        # ── Premium — TWO-STAGE MODEL ──────────────────────
                        # Premium and churn are CONCURRENT independent risks.
                        # A customer can go premium THEN later churn, so we evaluate
                        # premium regardless of lifecycle_stage (which may be 'churned').
                        p_rng = get_customer_rng(customer_index, "premium", config.master_seed)
                        goes_premium = calculate_premium_decision(
                            country, income_band, config, p_rng
                        )
                        if goes_premium:
                            # Premium window = activation → min(churn_date, end_date)
                            effective_end = churn_date if churn_date else end_date
                            upgrade_date = generate_premium_timing(
                                activation_date, effective_end, config, p_rng
                            )
                            if upgrade_date is not None:
                                premium_status       = True
                                premium_upgrade_date = upgrade_date
                    else:
                        activation_date = None

            elif kyc_status == "rejected":
                lifecycle_stage = "kyc_rejected"
            elif kyc_status == "pending":
                lifecycle_stage = "kyc_pending"

            uid = hashlib.md5(f"{config.master_seed}:customer:{customer_index}".encode()).hexdigest()
            customer_uuid = f"{uid[:8]}-{uid[8:12]}-{uid[12:16]}-{uid[16:20]}-{uid[20:32]}"

            customers.append({
                "customer_id":            customer_index + 1,
                "customer_uuid":          customer_uuid,
                "signup_date":            signup_date,
                "country_code":           country,
                "channel_code":           channel,
                "age_group":              age_group,
                "gender":                 gender,
                "occupation":             occupation,
                "income_band":            income_band,
                "device_type":            device,
                "kyc_status":             kyc_status,
                "kyc_submission_date":    kyc_submission_date,
                "kyc_completion_date":    kyc_completion_date,
                "activation_date":        activation_date,
                "first_transaction_date": first_transaction_date,
                "premium_upgrade_date":   premium_upgrade_date,
                "last_activity_date":     last_activity_date,
                "churn_date":             churn_date,
                "lifecycle_stage":        lifecycle_stage,
                "premium_status":         premium_status,
                "customer_segment":       "registered",
                "product_count":          0,
                "total_revenue_gbp":      0.0,
                "is_test_customer":       False,
            })
            customer_index += 1

    df = pd.DataFrame(customers)
    activated_mask = df["lifecycle_stage"] == "activated"
    df.loc[activated_mask, "customer_segment"] = "occasional_user"

    out_path = Path(output_dir) / "dim_customer.parquet"
    df.to_parquet(out_path, index=False)

    stats = {
        "total":        len(df),
        "kyc_approved": int((df.kyc_status == "approved").sum()),
        "kyc_rejected": int((df.kyc_status == "rejected").sum()),
        "kyc_pending":  int((df.kyc_status == "pending").sum()),
        "activated":    int(df.lifecycle_stage.isin(["activated","churned"]).sum()),
        "churned":      int((df.lifecycle_stage == "churned").sum()),
        "premium":      int(df.premium_status.sum()),
    }
    logger.success(f"dim_customer v1.1: {len(df):,} rows → {out_path}")
    logger.info(f"Stats: {stats}")
    return df
