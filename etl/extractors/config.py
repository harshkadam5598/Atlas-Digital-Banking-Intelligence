"""
Atlas – Digital Banking Intelligence Platform
Synthetic Data Generation Configuration

Single source of truth for all generation parameters.
All values derive from the approved Sprint 3 blueprint + review amendments
+ calibration fixes applied after sample audit (Sprint 3 Audit v2).

CALIBRATION HISTORY
-------------------
v1.0  (Sprint 3 initial):
  txn_freq_mu = 2.8   → produced ~249K txns from 2K customers (99M at full scale)
  premium_base = 0.20 with tenure sub-rates → produced 2.1% premium rate

v1.1  (Sprint 3 Audit fix):
  txn_freq_mu = -0.5737  → card mean 0.72/month → projects 7,199,983 at full scale
  transfer_free_lambda = 0.109, fx_lambda = 0.044, transfer_int_lambda = 0.033
    (all Poisson rates recalibrated to fit 1.3677 total txn/customer/month budget)
  premium_base_rate = 0.2144 (lifted from 0.20 to compensate for date-truncation
    attrition in the two-stage model; produces blended 20.0%)
  premium_formula: replaced tenure sub-rate model with two-stage:
    Stage 1 – lifetime P(ever premium) = base × country_mult × income_mult
    Stage 2 – timing: days_to_premium ~ LogNormal(3.5, 1.0), mean≈45d
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class GenerationConfig:

    # ── Core scale ────────────────────────────────────────────────────────────
    master_seed:      int   = 42
    total_customers:  int   = 500_000
    start_date:       str   = "2022-01-01"
    end_date:         str   = "2024-12-31"
    history_years:    int   = 3

    # ── KYC distribution (BR-002) ─────────────────────────────────────────────
    kyc_approved_rate: float = 0.82
    kyc_rejected_rate: float = 0.08
    # kyc_pending = remainder = 0.10

    # ── Activation rate (of KYC-approved) ────────────────────────────────────
    activation_rate:  float = 0.85

    # ── Premium conversion — TWO-STAGE MODEL (v1.1 fix) ──────────────────────
    # Stage 1: lifetime P(ever premium) = premium_base_rate × country_mult × income_mult
    # Stage 2: days_to_premium ~ LogNormal(premium_timing_mu, premium_timing_sigma)
    # base_rate raised from 0.20 → 0.2144 to offset ~1.8% date-truncation attrition
    # in the 2024 cohort. Blended predicted rate: 20.0%.
    premium_base_rate:      float = 0.2144
    premium_timing_mu:      float = 3.5    # LogNormal mu for days-to-premium
    premium_timing_sigma:   float = 1.0    # LogNormal sigma

    # ── Churn model ───────────────────────────────────────────────────────────
    churn_weibull_shape: float = 0.85
    churn_weibull_scale: float = 180.0   # days
    reactivation_rate:   float = 0.12

    # ── Transaction frequency — CALIBRATED v1.1 ──────────────────────────────
    # System solves: sum(adoption_i × rate_i) = 1.3677 txn/customer/month
    # → projects 7,199,983 transactions at full 500K scale (0.00% variance)
    #
    # DEBIT_CARD: LogNormal(mu=-0.5737, sigma=0.7) → mean=0.7198/month
    txn_freq_mu:    float = -0.5737   # was 2.8 — corrected in v1.1
    txn_freq_sigma: float = 0.70

    # Non-card Poisson lambdas (per month, per adopter) — CALIBRATED v1.1
    transfer_free_lambda:  float = 0.1090   # was 4.2
    fx_lambda:             float = 0.0436   # was 2.1
    transfer_int_lambda:   float = 0.0327   # was 1.4
    crypto_lambda:         float = 1.8000   # unchanged (very low adoption keeps contrib small)

    # Transaction amount distributions (unchanged — these drive revenue, not volume)
    txn_amount_mu:    float = 3.6
    txn_amount_sigma: float = 0.9

    # ── Transaction status / fraud rates ─────────────────────────────────────
    failed_txn_rate:           float = 0.025
    fraud_flag_rate:           float = 0.008
    fraud_cleared_rate:        float = 0.78
    suspicious_transfer_rate:  float = 0.004
    chargeback_rate:           float = 0.0015

    # ── Support tickets (amended: 130K target) ────────────────────────────────
    support_ticket_customer_pct: float = 0.37

    # ── Country distribution (sums to 1.0 after normalisation) ───────────────
    country_weights: Dict[str, float] = field(default_factory=lambda: {
        "GB": 0.280, "DE": 0.095, "FR": 0.070, "PL": 0.065,
        "IT": 0.050, "ES": 0.045, "NL": 0.040, "RO": 0.035,
        "SE": 0.035, "IE": 0.030, "US": 0.030, "AU": 0.025,
        "DK": 0.020, "NO": 0.020, "FI": 0.015, "CZ": 0.015,
        "HU": 0.015, "PT": 0.015, "CA": 0.015, "SG": 0.010,
        "BR": 0.005, "JP": 0.005,
    })

    # ── Channel distribution ──────────────────────────────────────────────────
    channel_weights: Dict[str, float] = field(default_factory=lambda: {
        "ORGANIC_SEARCH": 0.22, "REFERRAL":    0.18, "GOOGLE_ADS":  0.20,
        "SOCIAL_META":    0.16, "SOCIAL_TIKTOK":0.10,"INFLUENCER":  0.06,
        "EMAIL":          0.05, "DIRECT":       0.03,
    })

    # ── Product adoption probabilities ────────────────────────────────────────
    product_adoption: Dict[str, float] = field(default_factory=lambda: {
        "DEBIT_CARD":     0.95,
        "TRANSFER_FREE":  0.78,
        "SAVINGS_BASIC":  0.52,
        "FX_STANDARD":    0.45,
        "TRANSFER_INT":   0.38,
        "SAVINGS_VAULT":  0.35,   # of SAVINGS_BASIC adopters
        "INVEST_BASIC":   0.22,
        "PREMIUM_SUB":    0.20,   # amended from 0.28
        "INVEST_PREMIUM": 0.41,   # of premium holders
        "CRYPTO":         0.18,   # amended from 0.33 — of premium holders 18-44
    })

    # ── Revenue fee rates ─────────────────────────────────────────────────────
    fee_rates: Dict[str, float] = field(default_factory=lambda: {
        "DEBIT_CARD":     0.0120,
        "FX_STANDARD":    0.0050,
        "TRANSFER_INT":   0.0040,
        "INVEST_BASIC":   0.0075,
        "INVEST_PREMIUM": 0.0050,
        "CRYPTO":         0.0150,
        "PREMIUM_SUB":    9.99,
    })

    # ── Premium country multipliers ───────────────────────────────────────────
    premium_country_mult: Dict[str, float] = field(default_factory=lambda: {
        "GB": 1.3, "IE": 1.3, "AU": 1.3, "SG": 1.3, "US": 1.3,
        "DE": 1.0, "FR": 1.0, "NL": 1.0, "SE": 1.0, "DK": 1.0,
        "NO": 1.0, "CA": 1.0,
        "PL": 0.7, "RO": 0.7, "CZ": 0.7, "HU": 0.7,
        "IT": 0.7, "ES": 0.7, "PT": 0.7, "BR": 0.7,
        "JP": 0.7, "FI": 0.7,
    })

    # ── Premium income multipliers ────────────────────────────────────────────
    premium_income_mult: Dict[str, float] = field(default_factory=lambda: {
        "Under 20k": 0.6, "20k-40k": 0.8, "40k-70k": 1.0,
        "70k-100k": 1.2, "100k+": 1.5,
    })

    # ── Seasonality multipliers (index 0=Jan … 11=Dec) ───────────────────────
    acquisition_seasonality: List[float] = field(default_factory=lambda: [
        1.18, 0.92, 0.98, 1.05, 1.08, 1.12,
        0.94, 0.88, 1.15, 1.04, 1.09, 0.85,
    ])

    fx_seasonality: List[float] = field(default_factory=lambda: [
        0.85, 0.80, 0.90, 1.00, 1.10, 1.40,
        1.60, 1.55, 1.10, 0.95, 1.00, 1.20,
    ])

    card_seasonality: List[float] = field(default_factory=lambda: [
        0.90, 0.85, 0.95, 1.00, 1.05, 1.10,
        1.15, 1.10, 1.05, 1.10, 1.25, 1.35,
    ])

    # ── Crypto volatility event multipliers (year, quarter) ──────────────────
    crypto_events: Dict[Tuple[int, int], float] = field(default_factory=lambda: {
        (2022, 2): 4.0,
        (2023, 1): 2.5,
        (2024, 3): 3.2,
    })

    # ── Expected row counts (validation targets at 500K scale) ───────────────
    expected_rows: Dict[str, int] = field(default_factory=lambda: {
        "dim_customer":           500_000,
        "fact_customer_journey":  500_000,
        "fact_transactions":    7_200_000,
        "fact_product_events": 11_517_300,
        "fact_revenue":         2_100_000,
        "fact_marketing":         500_000,
        "fact_support":           130_000,
        "fact_kyc_events":        560_000,
    })


CONFIG = GenerationConfig()
