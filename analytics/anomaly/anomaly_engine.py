"""
Atlas Anomaly Detection Engine

Automatically detects unusual business behaviour: revenue drops/spikes,
fraud spikes, KYC processing delays, transaction failure spikes,
country-specific anomalies, and product adoption anomalies.

Detection method: rolling z-score against a trailing historical baseline.
A data point is anomalous if it deviates from the trailing mean by more
than `Z_THRESHOLD` standard deviations. This is the simplest statistically
defensible anomaly detection method, consistent with the Forecast Engine's
"interpretability over complexity" principle — every anomaly's
detection_reason states the exact z-score and baseline so it is auditable.

Severity is derived directly from the z-score magnitude, not a separate
hardcoded judgement call per metric.
"""

from __future__ import annotations

from datetime import date
from typing import List, Optional

import numpy as np
import pandas as pd
from loguru import logger

from analytics.core.data_context import DataContext, get_data_context
from analytics.core.types import Anomaly, Severity
from analytics.kpis.periods import safe_ratio

Z_THRESHOLD = 2.0          # minimum |z-score| to flag as anomalous
MIN_BASELINE_PERIODS = 4   # below this, baseline is too thin to trust


def _severity_from_zscore(z: float) -> Severity:
    az = abs(z)
    if az >= 4.0:
        return Severity.CRITICAL
    if az >= 3.0:
        return Severity.HIGH
    if az >= 2.5:
        return Severity.MEDIUM
    return Severity.LOW


def _zscore_series(values: pd.Series) -> pd.Series:
    """Z-score each point against the trailing mean/std excluding itself (leave-one-out)."""
    n = len(values)
    z = pd.Series([0.0] * n, index=values.index)
    for i in range(n):
        baseline = values.drop(values.index[i])
        if len(baseline) < MIN_BASELINE_PERIODS or baseline.std() == 0:
            continue
        z.iloc[i] = (values.iloc[i] - baseline.mean()) / baseline.std()
    return z


def detect_revenue_anomalies(ctx: Optional[DataContext] = None) -> List[Anomaly]:
    """
    Detect revenue drops and spikes: monthly net revenue z-scored against
    the trailing history of all other months.
    """
    ctx = ctx or get_data_context()
    rev = ctx.get("fact_revenue")
    if not len(rev):
        return []

    monthly = rev.copy()
    monthly["period"] = monthly["revenue_date"].dt.to_period("M")
    series = monthly.groupby("period")["net_revenue_gbp"].sum()
    if len(series) < MIN_BASELINE_PERIODS + 1:
        return []

    z_scores = _zscore_series(series)
    anomalies = []
    for period, z in z_scores.items():
        if abs(z) < Z_THRESHOLD:
            continue
        baseline = series.drop(period)
        expected = float(baseline.mean())
        observed = float(series[period])
        deviation_pct = round(safe_ratio(observed - expected, expected) * 100, 1) if expected else 0.0

        direction = "spike" if z > 0 else "drop"
        anomalies.append(Anomaly(
            metric="revenue",
            detected_at=period.to_timestamp().date(),
            severity=_severity_from_zscore(z),
            observed_value=round(observed, 2),
            expected_value=round(expected, 2),
            deviation_pct=deviation_pct,
            detection_reason=(
                f"Monthly net revenue z-score={z:.2f} vs trailing baseline "
                f"(mean=£{expected:,.0f}, n={len(baseline)} months)"
            ),
            business_impact=(
                f"Revenue {direction} of {abs(deviation_pct):.1f}% in {period} "
                f"versus the typical monthly pattern."
            ),
            suggested_investigation=(
                "Check for product launches, pricing changes, churn events, "
                "or data pipeline issues coinciding with this period."
                if direction == "drop" else
                "Confirm this is genuine growth (campaign, seasonality) rather "
                "than a one-off or data duplication artefact."
            ),
        ))
    return anomalies


def detect_fraud_anomalies(ctx: Optional[DataContext] = None) -> List[Anomaly]:
    """
    Detect fraud-rate spikes by month, z-scored against trailing history.

    Computes fraud_flagged events as a rate per 1,000 completed transactions
    rather than raw count.  A month with higher transaction volume naturally
    produces more flag events; normalising by volume eliminates those false
    positives and surfaces genuine deterioration in the fraud signal quality.

    Severity and z-score methodology are unchanged from the original detector.
    """
    ctx = ctx or get_data_context()
    evt = ctx.get("fact_product_events")
    txn = ctx.get("fact_transactions")
    if not len(evt) or not len(txn):
        return []

    fraud_evt = evt[evt["event_type"] == "fraud_flagged"].copy()
    if not len(fraud_evt):
        return []

    # Monthly completed transaction volume — the denominator
    txn_work = txn.copy()
    txn_work["period"] = txn_work["transaction_date"].dt.to_period("M")
    completed_txn = txn_work[txn_work["status"] == "completed"]
    txn_counts = completed_txn.groupby("period").size()
    if not len(txn_counts):
        return []

    fraud_evt["period"] = fraud_evt["event_date"].dt.to_period("M")
    fraud_counts = fraud_evt.groupby("period").size()

    # Align on common periods; periods with no completed transactions are dropped
    common = fraud_counts.index.intersection(txn_counts.index)
    if len(common) < MIN_BASELINE_PERIODS + 1:
        return []

    # Rate per 1,000 completed transactions
    rate_series = (fraud_counts.reindex(common).fillna(0)
                   / txn_counts.reindex(common)) * 1000

    anomalies = []
    for period in rate_series.index:
        z = _zscore_or_pct(rate_series, period)
        if z < Z_THRESHOLD:   # only flag upward spikes
            continue
        baseline = rate_series.drop(period)
        expected = float(baseline.mean())
        observed = float(rate_series[period])
        deviation_pct = round(safe_ratio(observed - expected, expected) * 100, 1) if expected else 0.0
        raw_flags = int(fraud_counts.get(period, 0))

        anomalies.append(Anomaly(
            metric="fraud_rate",
            detected_at=period.to_timestamp().date(),
            severity=_severity_from_zscore(z),
            observed_value=round(observed, 2),
            expected_value=round(expected, 2),
            deviation_pct=deviation_pct,
            detection_reason=(
                f"Fraud rate z-score={z:.2f} vs trailing baseline "
                f"(mean={expected:.2f} flags/1k txns, n={len(baseline)} months); "
                f"{raw_flags} raw fraud_flagged events this period"
            ),
            business_impact=(
                f"Fraud rate reached {observed:.2f} per 1,000 transactions in {period}, "
                f"{deviation_pct:+.0f}% above the typical rate — "
                f"not attributable to higher transaction volume alone."
            ),
            suggested_investigation=(
                "Cross-reference flagged transactions for a common merchant, "
                "country, or product pattern; verify detection rule "
                "thresholds have not been miscalibrated."
            ),
        ))
    return anomalies


def detect_kyc_delay_anomalies(ctx: Optional[DataContext] = None) -> List[Anomaly]:
    """Detect months where median KYC processing time spikes above trailing baseline."""
    ctx = ctx or get_data_context()
    kyc = ctx.get("fact_kyc_events")
    if not len(kyc):
        return []

    kyc = kyc.dropna(subset=["processing_time_hours"]).copy()
    if not len(kyc):
        return []
    kyc["period"] = kyc["submission_date"].dt.to_period("M")
    series = kyc.groupby("period")["processing_time_hours"].median()
    if len(series) < MIN_BASELINE_PERIODS + 1:
        return []

    z_scores = _zscore_series(series)
    anomalies = []
    for period, z in z_scores.items():
        if z < Z_THRESHOLD:
            continue
        baseline = series.drop(period)
        expected = float(baseline.mean())
        observed = float(series[period])
        deviation_pct = round(safe_ratio(observed - expected, expected) * 100, 1) if expected else 0.0

        anomalies.append(Anomaly(
            metric="kyc_processing_time",
            detected_at=period.to_timestamp().date(),
            severity=_severity_from_zscore(z),
            observed_value=round(observed, 1),
            expected_value=round(expected, 1),
            deviation_pct=deviation_pct,
            detection_reason=(
                f"Median KYC processing time z-score={z:.2f} vs trailing baseline "
                f"(mean={expected:.1f}h, n={len(baseline)} months)"
            ),
            business_impact=(
                f"KYC processing took {observed:.1f}h in {period} vs the usual "
                f"{expected:.1f}h, directly delaying customer activation."
            ),
            suggested_investigation=(
                "Check KYC vendor/provider status, reviewer staffing levels, "
                "and whether rejection-resubmission volume increased."
            ),
        ))
    return anomalies


def detect_transaction_failure_anomalies(ctx: Optional[DataContext] = None) -> List[Anomaly]:
    """Detect months where the failed-transaction rate spikes above trailing baseline."""
    ctx = ctx or get_data_context()
    txn = ctx.get("fact_transactions")
    if not len(txn):
        return []

    work = txn.copy()
    work["period"] = work["transaction_date"].dt.to_period("M")
    rates = work.groupby("period")["status"].apply(
        lambda s: safe_ratio((s == "failed").sum(), len(s)) * 100
    )
    if len(rates) < MIN_BASELINE_PERIODS + 1:
        return []

    z_scores = _zscore_series(rates)
    anomalies = []
    for period, z in z_scores.items():
        if z < Z_THRESHOLD:
            continue
        baseline = rates.drop(period)
        expected = float(baseline.mean())
        observed = float(rates[period])
        deviation_pct = round(safe_ratio(observed - expected, expected) * 100, 1) if expected else 0.0

        anomalies.append(Anomaly(
            metric="failed_transaction_rate",
            detected_at=period.to_timestamp().date(),
            severity=_severity_from_zscore(z),
            observed_value=round(observed, 2),
            expected_value=round(expected, 2),
            deviation_pct=deviation_pct,
            detection_reason=(
                f"Failed transaction rate z-score={z:.2f} vs trailing baseline "
                f"(mean={expected:.2f}%, n={len(baseline)} months)"
            ),
            business_impact=(
                f"{observed:.2f}% transaction failure rate in {period}, "
                f"{deviation_pct:+.0f}% above baseline — likely customer-facing impact."
            ),
            suggested_investigation=(
                "Check payment processor status, specific failure_reason "
                "distribution for this period, and any concurrent product "
                "or infrastructure changes."
            ),
        ))
    return anomalies


def detect_country_anomalies(ctx: Optional[DataContext] = None) -> List[Anomaly]:
    """
    Detect country-specific revenue anomalies across the full historical window.

    Per-country baseline methodology is preserved: each country is compared
    only to its own history, not cross-country, because countries differ
    substantially in absolute revenue scale.

    The original implementation evaluated only the latest period for each
    country.  This revision evaluates all historical periods using the same
    leave-one-out z-score applied by every other time-series detector in this
    engine, so anomalies that occurred mid-history are not silently discarded.
    """
    ctx = ctx or get_data_context()
    rev = ctx.get("fact_revenue")
    if not len(rev):
        return []

    work = rev.copy()
    work["period"] = work["revenue_date"].dt.to_period("M")
    pivot = work.groupby(["country_code", "period"])["net_revenue_gbp"].sum().unstack(fill_value=0.0)

    anomalies = []
    for country in pivot.index:
        series = pivot.loc[country]
        if len(series) < MIN_BASELINE_PERIODS + 1:
            continue
        z_scores = _zscore_series(series)

        # Evaluate every period, not only the last one
        for period, z in z_scores.items():
            if abs(z) < Z_THRESHOLD:
                continue

            baseline = series.drop(period)
            expected = float(baseline.mean())
            observed = float(series[period])
            if expected == 0 and observed == 0:
                continue
            deviation_pct = round(safe_ratio(observed - expected, expected) * 100, 1) if expected else 0.0

            anomalies.append(Anomaly(
                metric="revenue",
                detected_at=period.to_timestamp().date(),
                severity=_severity_from_zscore(z),
                observed_value=round(observed, 2),
                expected_value=round(expected, 2),
                deviation_pct=deviation_pct,
                detection_reason=(
                    f"{country} revenue z-score={z:.2f} vs its own trailing baseline "
                    f"(mean=£{expected:,.0f}, n={len(baseline)} months)"
                ),
                business_impact=(
                    f"{country} revenue {'spiked' if z > 0 else 'dropped'} "
                    f"{abs(deviation_pct):.1f}% in {period} relative to its own history."
                ),
                suggested_investigation=(
                    f"Check for {country}-specific regulatory changes, local "
                    f"competitor activity, FX rate moves, or marketing campaign timing."
                ),
                dimension=f"country={country}",
            ))
    return anomalies


def detect_product_adoption_anomalies(ctx: Optional[DataContext] = None) -> List[Anomaly]:
    """
    Detect product-specific adoption anomalies: products whose monthly
    active-user count deviates sharply from their own trailing baseline.
    """
    ctx = ctx or get_data_context()
    evt = ctx.get("fact_product_events")
    if not len(evt):
        return []

    work = evt.copy()
    work["period"] = work["event_date"].dt.to_period("M")
    pivot = work.groupby(["product_code", "period"])["customer_id"].nunique().unstack(fill_value=0)

    anomalies = []
    for product in pivot.index:
        series = pivot.loc[product]
        if len(series) < MIN_BASELINE_PERIODS + 1:
            continue
        z_scores = _zscore_series(series)
        last_period = series.index[-1]
        z = z_scores[last_period]
        if abs(z) < Z_THRESHOLD:
            continue

        baseline = series.drop(last_period)
        expected = float(baseline.mean())
        observed = float(series[last_period])
        deviation_pct = round(safe_ratio(observed - expected, expected) * 100, 1) if expected else 0.0

        anomalies.append(Anomaly(
            metric="product_adoption",
            detected_at=last_period.to_timestamp().date(),
            severity=_severity_from_zscore(z),
            observed_value=observed,
            expected_value=round(expected, 1),
            deviation_pct=deviation_pct,
            detection_reason=(
                f"{product} active users z-score={z:.2f} vs its own trailing "
                f"baseline (mean={expected:.1f}/month, n={len(baseline)} months)"
            ),
            business_impact=(
                f"{product} adoption {'spiked' if z > 0 else 'dropped'} "
                f"{abs(deviation_pct):.1f}% in {last_period}."
            ),
            suggested_investigation=(
                f"Check for a {product} feature launch, outage, pricing change, "
                f"or marketing push coinciding with this period."
            ),
            dimension=f"product={product}",
        ))
    return anomalies



def _zscore_or_pct(series: pd.Series, idx) -> float:
    """
    Return the z-score for `series[idx]` against the rest of the series.

    When the baseline has zero standard deviation (all other values are
    identical) _zscore_series() correctly returns 0.0 — mathematically sound
    but unhelpful for degenerate series where a single spike stands out visually.
    In those cases this helper returns a pseudo-z derived from the percentage
    deviation, using a conservative divisor of 30 so the classification stays
    proportionate: a 100% spike (double the baseline) → pseudo-z ≈ 3.3 (HIGH).

    This does not change _zscore_series() or any existing detector.
    """
    baseline = series.drop(idx)
    if len(baseline) < MIN_BASELINE_PERIODS:
        return 0.0
    std = baseline.std()
    if std == 0:
        mean = baseline.mean()
        if mean == 0:
            return 0.0
        # percentage deviation / 30 gives a proportionate pseudo-z:
        # +100% spike  → ~3.3 (HIGH)
        # +50% spike   → ~1.7 (below threshold — no false positives)
        # -100% drop   → ~-3.3 (HIGH)
        return (series[idx] - mean) / mean / 0.30
    return (series[idx] - baseline.mean()) / std


def detect_customer_behavior_anomalies(ctx: Optional[DataContext] = None) -> List[Anomaly]:
    """
    Detect customer behaviour anomalies using three independent signals derived
    from dim_customer date columns:

      1. MAU decline       — customers whose last_activity_date falls within each
                             calendar month, z-scored against the trailing series.
                             Only downward deviations (MAU drops) are flagged.
      2. Activation decline — new activations per month (activation_date),
                             z-scored against trailing history.
                             Only downward deviations are flagged.
      3. Churn spike       — customers whose churn_date falls in a given month,
                             z-scored against trailing history.
                             Only upward deviations are flagged.

    Uses _zscore_or_pct() instead of _zscore_series() so that a single-spike
    pattern against an otherwise flat baseline is still detected (the shared
    _zscore_series() returns 0 when baseline std == 0, which is mathematically
    correct but suppresses detection on degenerate series).

    Severity maps from the effective z-score magnitude via _severity_from_zscore().

    Premium conversion deterioration is intentionally excluded: it requires
    a multi-period KPI time series from the KPI registry, which belongs to the
    insight engine's movement detection path, not the raw count approach used
    throughout this engine.
    """
    ctx = ctx or get_data_context()
    cust = ctx.get("dim_customer")
    if not len(cust):
        return []

    cust = cust.copy()
    for col in ["last_activity_date", "activation_date", "churn_date"]:
        if col in cust.columns:
            cust[col] = pd.to_datetime(cust[col], errors="coerce")

    anomalies: List[Anomaly] = []

    # ── Signal 1: MAU — monthly active customers ───────────────────────────
    if "last_activity_date" in cust.columns:
        active = cust[cust["last_activity_date"].notna()].copy()
        if len(active):
            active["period"] = active["last_activity_date"].dt.to_period("M")
            mau_series = active.groupby("period")["customer_id"].nunique()

            if len(mau_series) >= MIN_BASELINE_PERIODS + 1:
                for period in mau_series.index:
                    z = _zscore_or_pct(mau_series, period)
                    if z >= -Z_THRESHOLD:        # only flag downward
                        continue
                    baseline = mau_series.drop(period)
                    expected = float(baseline.mean())
                    observed = float(mau_series[period])
                    deviation_pct = round(
                        safe_ratio(observed - expected, expected) * 100, 1
                    ) if expected else 0.0

                    anomalies.append(Anomaly(
                        metric="monthly_active_users",
                        detected_at=period.to_timestamp().date(),
                        severity=_severity_from_zscore(z),
                        observed_value=round(observed),
                        expected_value=round(expected, 1),
                        deviation_pct=deviation_pct,
                        detection_reason=(
                            f"MAU z-score={z:.2f} vs trailing baseline "
                            f"(mean={expected:.0f} active customers/month, "
                            f"n={len(baseline)} months)"
                        ),
                        business_impact=(
                            f"Monthly active users dropped to {int(observed):,} in {period}, "
                            f"{abs(deviation_pct):.1f}% below the typical monthly level — "
                            f"a leading indicator of revenue decline."
                        ),
                        suggested_investigation=(
                            "Review churn cohort for this period, check whether "
                            "new activation rates also declined, and cross-reference "
                            "with support ticket volume for customer experience issues."
                        ),
                    ))

    # ── Signal 2: Activation decline — new activations per month ──────────
    if "activation_date" in cust.columns:
        activated = cust[cust["activation_date"].notna()].copy()
        if len(activated):
            activated["period"] = activated["activation_date"].dt.to_period("M")
            act_series = activated.groupby("period")["customer_id"].nunique()

            if len(act_series) >= MIN_BASELINE_PERIODS + 1:
                for period in act_series.index:
                    z = _zscore_or_pct(act_series, period)
                    if z >= -Z_THRESHOLD:        # only flag downward
                        continue
                    baseline = act_series.drop(period)
                    expected = float(baseline.mean())
                    observed = float(act_series[period])
                    deviation_pct = round(
                        safe_ratio(observed - expected, expected) * 100, 1
                    ) if expected else 0.0

                    anomalies.append(Anomaly(
                        metric="customer_activations",
                        detected_at=period.to_timestamp().date(),
                        severity=_severity_from_zscore(z),
                        observed_value=round(observed),
                        expected_value=round(expected, 1),
                        deviation_pct=deviation_pct,
                        detection_reason=(
                            f"New activations z-score={z:.2f} vs trailing baseline "
                            f"(mean={expected:.0f} activations/month, "
                            f"n={len(baseline)} months)"
                        ),
                        business_impact=(
                            f"Only {int(observed):,} new customers activated in {period}, "
                            f"{abs(deviation_pct):.1f}% below the typical monthly rate — "
                            f"reduces near-term revenue pipeline."
                        ),
                        suggested_investigation=(
                            "Check KYC approval rate and processing time for this period, "
                            "review acquisition funnel conversion rates, and verify "
                            "no onboarding product issue coincided with this month."
                        ),
                    ))

    # ── Signal 3: Churn spike — customers churned per month ───────────────
    if "churn_date" in cust.columns:
        churned = cust[cust["churn_date"].notna()].copy()
        if len(churned):
            churned["period"] = churned["churn_date"].dt.to_period("M")
            churn_series = churned.groupby("period")["customer_id"].nunique()

            if len(churn_series) >= MIN_BASELINE_PERIODS + 1:
                for period in churn_series.index:
                    z = _zscore_or_pct(churn_series, period)
                    if z < Z_THRESHOLD:          # only flag upward
                        continue
                    baseline = churn_series.drop(period)
                    expected = float(baseline.mean())
                    observed = float(churn_series[period])
                    deviation_pct = round(
                        safe_ratio(observed - expected, expected) * 100, 1
                    ) if expected else 0.0

                    anomalies.append(Anomaly(
                        metric="customer_churn",
                        detected_at=period.to_timestamp().date(),
                        severity=_severity_from_zscore(z),
                        observed_value=round(observed),
                        expected_value=round(expected, 1),
                        deviation_pct=deviation_pct,
                        detection_reason=(
                            f"Churned customers z-score={z:.2f} vs trailing baseline "
                            f"(mean={expected:.0f} churns/month, "
                            f"n={len(baseline)} months)"
                        ),
                        business_impact=(
                            f"{int(observed):,} customers churned in {period}, "
                            f"{deviation_pct:+.0f}% above the typical monthly rate — "
                            f"compounding revenue loss if unaddressed."
                        ),
                        suggested_investigation=(
                            "Segment churned customers by acquisition cohort, "
                            "country, and product usage to identify the highest-risk "
                            "profile; check whether a specific product change or "
                            "support issue preceded this churn spike."
                        ),
                    ))

    return anomalies

DETECTION_FUNCTIONS = [
    detect_revenue_anomalies,
    detect_fraud_anomalies,
    detect_kyc_delay_anomalies,
    detect_transaction_failure_anomalies,
    detect_country_anomalies,
    detect_product_adoption_anomalies,
    detect_customer_behavior_anomalies,
]


def detect_all_anomalies(ctx: Optional[DataContext] = None) -> List[Anomaly]:
    """
    Run every detection function and return all anomalies found, sorted
    by severity (critical first) then by detected_at (most recent first).
    """
    ctx = ctx or get_data_context()
    severity_order = {Severity.CRITICAL: 0, Severity.HIGH: 1, Severity.MEDIUM: 2, Severity.LOW: 3}

    all_anomalies: List[Anomaly] = []
    for fn in DETECTION_FUNCTIONS:
        try:
            all_anomalies.extend(fn(ctx))
        except Exception as e:
            logger.warning(f"[AnomalyEngine] '{fn.__name__}' failed: {e}")

    all_anomalies.sort(key=lambda a: (severity_order[a.severity], a.detected_at), reverse=False)
    all_anomalies.sort(key=lambda a: severity_order[a.severity])
    logger.info(f"[AnomalyEngine] {len(all_anomalies)} anomalies detected "
               f"across {len(DETECTION_FUNCTIONS)} detectors")
    return all_anomalies
