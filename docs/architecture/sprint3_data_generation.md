# Atlas – Sprint 3: Synthetic Data Generation Architecture

**Status:** Complete — all fixes applied, validated, reproducibility confirmed.
**Generator version:** 1.0.0 | **Master seed:** 42

---

## Architecture Overview

```
GenerationConfig (frozen dataclass)
         │
         ├── SeedManager (deterministic MD5 child seeds per domain)
         │
         ├── CustomerGenerator     → dim_customer + fact_customer_journey
         ├── KYCGenerator          → fact_kyc_events
         ├── MarketingGenerator    → fact_marketing
         ├── TransactionGenerator  → fact_transactions
         ├── ProductEventGenerator → fact_product_events (incl. fraud events)
         ├── SupportGenerator      → fact_support
         └── RevenueDeriver        → fact_revenue (from transactions)
                   │
         DataValidator (4 layers)
                   │
         ReproducibilityProof (SHA-256 fingerprints)
```

---

## Fix Log (Sprint 3 Review Cycle)

### Fix 1 — Transaction Frequency Calibration

**Problem:** `txn_freq_mu = 2.8` (LogNormal mean = 21 txn/month for card) combined
with non-card Poisson lambdas (4.2, 2.1, 1.4) produced ~99M transactions at full
scale vs the 7.2M blueprint target.

**Root cause:** The LogNormal parameter governs monthly frequency per adopter. At
mean 21 card txn/month × 95% adoption × 5.26M customer-months = 104M card
transactions alone.

**Fix applied:**

| Parameter | Before | After | Rationale |
|---|---|---|---|
| `txn_freq_mu` | 2.8 | **-0.9304** | LogNormal mean: 21 → 0.504/month |
| `transfer_free_lambda` | 4.2 | **0.4384** | Poisson mean calibrated |
| `transfer_int_lambda` | 1.4 | **0.2879** | Calibrated to 576K target |
| `fx_lambda` | 2.1 | **0.2431** | Calibrated to 576K target |
| `crypto_lambda` | 1.8 | **1.5197** | Kept higher (trade-intensive) |

**Derivation:** 7,200,000 ÷ 5,264,300 customer-months = 1.368 combined txn/month.
Split by transaction type mix (35% card, 25% local transfer, 8% intl, 8% FX, 10%
subscription, 5% invest, 4% crypto). Each product rate = type-target ÷ (total_cm ×
adoption_rate).

**Result:** Sample monthly rate dropped from 18.8 to 1.07 txn/customer/month. Full-
scale projection: **7,699,031** (+6.9% vs 7.2M target). Within 15% tolerance. ✓

---

### Fix 2 — Premium Conversion Formula

**Problem A — Formula bug:** Original code:
```python
p = base_rate × (tenure_factor / 0.20) × country_mult × income_mult
```
Dividing by 0.20 cancelled `base_rate`, producing only the tenure sub-rate × mults.
Result: 2.1% conversion vs 20% target.

**Fix:** Replaced `premium_tenure_rates` with `premium_tenure_mults` — pure scale
factors on `base_rate`. Calibrated so population-weighted average = 1.0, making
blended conversion = `base_rate = 0.20` exactly.

```python
# Corrected formula:
p = base_rate × tenure_mult × country_mult × income_mult
```

| Tenure band | Multiplier | Rationale |
|---|---|---|
| 0–7 days | 0.1726 | Still evaluating — very low intent |
| 8–30 days | 0.9490 | Onboarding window opens |
| 31–90 days | **2.0706** | Peak: first value realised, highest intent |
| 91–180 days | 1.7255 | Second conversion window |
| 181–365 days | 1.1216 | Feature-triggered late conversions |
| 365+ days | 0.6902 | Long-tail uncommitted free users |

**Problem B — Logic gate bug:** The premium decision included `and lifecycle_stage ==
"activated"` which executed after churn was already assigned. 70% of sample customers
were churned (long-tenured early cohort), making them ineligible. Churn and premium
are sequential — a customer can be premium, then later churn.

**Fix:** Removed lifecycle gate. Premium is now evaluated for all activated customers
regardless of subsequent churn status. Churn cannot retroactively block premium.

**Result:** Premium conversion rose from 2.1% → **17.95%** (within 17–23% band). ✓

---

## Validated Parameters

### Generation Scale
| Parameter | Value |
|---|---|
| Total customers | 500,000 |
| Activated (est.) | ~351,600 (82% KYC × 85% activation) |
| History window | 2022-01-01 → 2024-12-31 |
| Master seed | 42 |

### Expected Full-Scale Row Counts
| Table | Target | Tolerance | Notes |
|---|---|---|---|
| `dim_customer` | 500,000 | ±0.1% | |
| `fact_customer_journey` | 500,000 | ±0.1% | |
| `fact_transactions` | ~7,700,000 | ±15% | Revised up from 7.2M (+6.9% projection) |
| `fact_product_events` | ~11,500,000 | ±10% | |
| `fact_revenue` | ~2,100,000 | ±10% | |
| `fact_marketing` | 500,000 | ±0.1% | |
| `fact_support` | ~130,000 | ±20% | |
| `fact_kyc_events` | ~560,000 | ±5% | |

### Reproducibility Guarantee
- Two independent runs with `--sample 2000` produce **identical SHA-256 fingerprints**.
- Fingerprint: `4d6dd314e6aa44197602f57dab624e4c619635e9f4a97c14982918a7910cc9b4`
- Mechanism: MD5-derived child seeds per domain per customer index.
- Changing seed from 42 to any other value produces a completely different but
  internally consistent dataset.

---

## Running Sprint 3

```bash
# Sample run (2K customers, ~9 seconds)
python -m etl.extractors.pipeline_orchestrator --sample 2000

# Full production run (500K customers — estimated 25-40 minutes)
python -m etl.extractors.pipeline_orchestrator

# Force regeneration (ignores checkpoints)
python -m etl.extractors.pipeline_orchestrator --force
```
