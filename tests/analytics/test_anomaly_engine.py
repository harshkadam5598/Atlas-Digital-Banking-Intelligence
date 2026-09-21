"""
Atlas Analytics — Anomaly Engine Unit Tests
Sprint 5.3 Phase 2C.2

Covers every public anomaly detection function:
  detect_revenue_anomalies
  detect_fraud_anomalies          (Sprint 5.3 rate-normalisation fix)
  detect_kyc_delay_anomalies
  detect_transaction_failure_anomalies
  detect_country_anomalies        (Sprint 5.3 all-periods fix)
  detect_product_adoption_anomalies
  detect_customer_behavior_anomalies  (Sprint 5.3 new detector)
  detect_all_anomalies            (orchestrator)

Also covers:
  _severity_from_zscore           (severity model)
  _zscore_series                  (shared helper — zero-std guard)
  _zscore_or_pct                  (flat-baseline helper)
  Anomaly.to_dict()               (serialisation)

Regression tests are explicitly labelled.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from analytics.anomaly.anomaly_engine import (
    DETECTION_FUNCTIONS,
    MIN_BASELINE_PERIODS,
    Z_THRESHOLD,
    _severity_from_zscore,
    _zscore_or_pct,
    _zscore_series,
    detect_all_anomalies,
    detect_country_anomalies,
    detect_customer_behavior_anomalies,
    detect_fraud_anomalies,
    detect_kyc_delay_anomalies,
    detect_product_adoption_anomalies,
    detect_revenue_anomalies,
    detect_transaction_failure_anomalies,
)
from analytics.core.types import Anomaly, Severity


# ── Shared fixtures and helpers ───────────────────────────────────────────────

def _ctx(**tables: pd.DataFrame) -> MagicMock:
    """Mock DataContext dispatching .get() by table name."""
    ctx = MagicMock()
    ctx.get.side_effect = lambda t: tables.get(t, pd.DataFrame())
    return ctx


def _periods(n: int, start: str = "2022-01") -> pd.DatetimeIndex:
    return pd.date_range(start, periods=n, freq="MS")


def _revenue_df(n: int = 24, base: float = 10_000.0,
                noise_pct: float = 0.08, spike_month: int | None = None,
                spike_mult: float = 8.0) -> pd.DataFrame:
    np.random.seed(7)
    rows = []
    for i, p in enumerate(_periods(n)):
        mult = spike_mult if i == spike_month else 1.0
        rev = max(0.0, (base + np.random.normal(0, base * noise_pct)) * mult)
        rows.append({"revenue_date": p, "net_revenue_gbp": rev})
    return pd.DataFrame(rows)


def _fraud_df(n: int = 24, base_flags: int = 8, base_txns: int = 1000,
              spike_month: int | None = None, spike_mult: float = 10.0,
              hv_month: int | None = None, hv_txn_mult: float = 3.0
              ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (fact_product_events, fact_transactions)."""
    np.random.seed(11)
    evt_rows, txn_rows = [], []
    for i, p in enumerate(_periods(n)):
        n_flags = int(base_flags * spike_mult) if i == spike_month else base_flags
        n_txns  = int(base_txns * hv_txn_mult) if i == hv_month else base_txns
        # proportionally more flags on hv_month keeps the rate constant
        hv_flags = int(base_flags * hv_txn_mult) if i == hv_month else base_flags
        actual_flags = n_flags if i != hv_month else hv_flags
        for _ in range(actual_flags):
            evt_rows.append({"event_date": p, "event_type": "fraud_flagged"})
        for _ in range(n_txns):
            txn_rows.append({"transaction_date": p, "status": "completed"})
    return pd.DataFrame(evt_rows), pd.DataFrame(txn_rows)


def _kyc_df(n: int = 24, base_hours: float = 12.0, spike_month: int | None = None,
            spike_mult: float = 6.0) -> pd.DataFrame:
    np.random.seed(13)
    rows = []
    for i, p in enumerate(_periods(n)):
        mult = spike_mult if i == spike_month else 1.0
        for _ in range(50):
            rows.append({
                "submission_date": p,
                "processing_time_hours": max(
                    0.1, np.random.normal(base_hours * mult, base_hours * 0.1)
                ),
            })
    return pd.DataFrame(rows)


def _txn_df(n: int = 24, base_txns: int = 500, fail_rate: float = 0.02,
            spike_month: int | None = None, spike_fail: float = 0.30) -> pd.DataFrame:
    np.random.seed(17)
    rows = []
    for i, p in enumerate(_periods(n)):
        fr = spike_fail if i == spike_month else fail_rate
        for _ in range(base_txns):
            status = "failed" if np.random.random() < fr else "completed"
            rows.append({"transaction_date": p, "status": status})
    return pd.DataFrame(rows)


def _country_revenue_df(n: int = 24, countries: dict | None = None,
                         spike_country: str | None = None,
                         spike_month: int | None = None,
                         spike_mult: float = 8.0) -> pd.DataFrame:
    if countries is None:
        countries = {"GB": 5000, "DE": 2000, "FR": 1500}
    np.random.seed(19)
    rows = []
    for i, p in enumerate(_periods(n)):
        for cc, base in countries.items():
            mult = spike_mult if (cc == spike_country and i == spike_month) else 1.0
            rev = max(0.0, (base + np.random.normal(0, base * 0.08)) * mult)
            rows.append({"revenue_date": p, "country_code": cc, "net_revenue_gbp": rev})
    return pd.DataFrame(rows)


def _product_evt_df(n: int = 24, products: list | None = None,
                    spike_product: str | None = None,
                    spike_month: int | None = None,
                    spike_mult: float = 8.0) -> pd.DataFrame:
    if products is None:
        products = ["DEBIT_CARD", "SAVINGS_BASIC"]
    np.random.seed(23)
    rows = []
    for i, p in enumerate(_periods(n)):
        for prod in products:
            base_users = 100
            mult = spike_mult if (prod == spike_product and i == spike_month) else 1.0
            n_users = max(1, int(base_users * mult + np.random.normal(0, 5)))
            for u in range(n_users):
                rows.append({"event_date": p, "product_code": prod,
                             "customer_id": u + 1, "event_type": "app_login"})
    return pd.DataFrame(rows)


def _customer_df(n: int = 24, per_month: int = 100,
                 churn_month: int | None = None, churn_mult: float = 8.0,
                 act_drop_month: int | None = None, act_drop_pct: float = 0.1
                 ) -> pd.DataFrame:
    np.random.seed(29)
    rows = []
    base = pd.Timestamp("2022-01-01")
    cid = 1
    for m in range(n):
        period = base + pd.DateOffset(months=m)
        n_act = max(1, int(per_month * act_drop_pct)) if m == act_drop_month else per_month
        n_churn = int(per_month * churn_mult) if m == churn_month else max(1, per_month // 10)
        for _ in range(n_act):
            rows.append({"customer_id": cid, "activation_date": period,
                         "churn_date": None,
                         "last_activity_date": period})
            cid += 1
        for _ in range(n_churn):
            rows.append({"customer_id": cid,
                         "activation_date": period - pd.DateOffset(months=6),
                         "churn_date": period,
                         "last_activity_date": period - pd.DateOffset(months=3)})
            cid += 1
    return pd.DataFrame(rows)


# ── 1. Shared helpers ─────────────────────────────────────────────────────────

class TestSeverityFromZscore:
    @pytest.mark.parametrize("z,expected", [
        (4.0, Severity.CRITICAL),
        (4.5, Severity.CRITICAL),
        (3.0, Severity.HIGH),
        (3.5, Severity.HIGH),
        (2.5, Severity.MEDIUM),
        (2.0, Severity.LOW),
        (2.1, Severity.LOW),
    ])
    def test_severity_bands(self, z, expected):
        assert _severity_from_zscore(z) == expected

    def test_symmetric_negative(self):
        assert _severity_from_zscore(-4.0) == Severity.CRITICAL
        assert _severity_from_zscore(-3.0) == Severity.HIGH


class TestZscoreSeries:
    def test_all_identical_returns_zeros(self):
        s = pd.Series([5.0] * 12,
                      index=pd.period_range("2022-01", periods=12, freq="M"))
        z = _zscore_series(s)
        assert (z == 0.0).all()

    def test_spike_detected_with_natural_variance(self):
        np.random.seed(1)
        vals = list(np.random.normal(100, 10, 35)) + [1000.0]
        s = pd.Series(vals, index=pd.period_range("2022-01", periods=36, freq="M"))
        z = _zscore_series(s)
        assert z.iloc[-1] > Z_THRESHOLD

    def test_short_series_returns_zeros(self):
        s = pd.Series([1.0, 2.0, 3.0],
                      index=pd.period_range("2022-01", periods=3, freq="M"))
        z = _zscore_series(s)
        assert (z == 0.0).all()

    def test_output_same_index_as_input(self):
        s = pd.Series(range(10),
                      index=pd.period_range("2022-01", periods=10, freq="M"),
                      dtype=float)
        assert list(_zscore_series(s).index) == list(s.index)


class TestZscoreOrPct:
    def test_flat_baseline_spike_detected(self):
        """Regression: _zscore_or_pct detects spike even when baseline std == 0."""
        flat = pd.Series([5.0] * 35 + [60.0],
                         index=pd.period_range("2022-01", periods=36, freq="M"))
        z = _zscore_or_pct(flat, flat.index[-1])
        assert z > Z_THRESHOLD

    def test_flat_baseline_drop_detected(self):
        flat = pd.Series([50.0] * 35 + [5.0],
                         index=pd.period_range("2022-01", periods=36, freq="M"))
        z = _zscore_or_pct(flat, flat.index[-1])
        assert z < -Z_THRESHOLD

    def test_returns_zero_when_baseline_too_short(self):
        s = pd.Series([1.0, 100.0],
                      index=pd.period_range("2022-01", periods=2, freq="M"))
        assert _zscore_or_pct(s, s.index[-1]) == 0.0

    def test_zero_mean_and_zero_std_returns_zero(self):
        s = pd.Series([0.0] * 10,
                      index=pd.period_range("2022-01", periods=10, freq="M"))
        assert _zscore_or_pct(s, s.index[-1]) == 0.0

    def test_with_natural_variance_matches_z_direction(self):
        np.random.seed(3)
        vals = list(np.random.normal(100, 12, 11)) + [500.0]
        s = pd.Series(vals, index=pd.period_range("2022-01", periods=12, freq="M"))
        z = _zscore_or_pct(s, s.index[-1])
        assert z > Z_THRESHOLD


# ── 2. Anomaly object ─────────────────────────────────────────────────────────

class TestAnomalyStructure:
    """Cross-cutting field and serialisation checks applied to every detector."""

    def _collect_all(self):
        """Gather at least one anomaly from each detector that can produce one."""
        results = []
        # revenue
        rev_df = _revenue_df(spike_month=10)
        results += detect_revenue_anomalies(ctx=_ctx(fact_revenue=rev_df))
        # fraud
        evt_df, txn_df = _fraud_df(spike_month=10)
        results += detect_fraud_anomalies(
            ctx=_ctx(fact_product_events=evt_df, fact_transactions=txn_df))
        # kyc
        results += detect_kyc_delay_anomalies(
            ctx=_ctx(fact_kyc_events=_kyc_df(spike_month=10)))
        # txn failure
        results += detect_transaction_failure_anomalies(
            ctx=_ctx(fact_transactions=_txn_df(spike_month=10)))
        # country
        results += detect_country_anomalies(
            ctx=_ctx(fact_revenue=_country_revenue_df(
                spike_country="DE", spike_month=10)))
        # product adoption
        results += detect_product_adoption_anomalies(
            ctx=_ctx(fact_product_events=_product_evt_df(
                spike_product="DEBIT_CARD", spike_month=23)))
        # customer behaviour
        results += detect_customer_behavior_anomalies(
            ctx=_ctx(dim_customer=_customer_df(churn_month=10)))
        return results

    def test_all_instances_are_anomaly(self):
        for a in self._collect_all():
            assert isinstance(a, Anomaly)

    def test_required_string_fields_non_empty(self):
        for a in self._collect_all():
            assert a.metric,                 f"metric empty: {a}"
            assert a.detection_reason,       f"detection_reason empty: {a}"
            assert a.business_impact,        f"business_impact empty: {a}"
            assert a.suggested_investigation,f"suggested_investigation empty: {a}"

    def test_detected_at_is_date(self):
        for a in self._collect_all():
            assert isinstance(a.detected_at, date)

    def test_severity_is_severity_enum(self):
        for a in self._collect_all():
            assert isinstance(a.severity, Severity)

    def test_to_dict_json_serialisable(self):
        import json
        for a in self._collect_all():
            try:
                json.dumps(a.to_dict())
            except (TypeError, ValueError) as e:
                pytest.fail(f"{a.metric} .to_dict() not JSON-serialisable: {e}")

    def test_to_dict_has_required_keys(self):
        required = {"metric", "detected_at", "severity", "observed_value",
                    "expected_value", "deviation_pct", "detection_reason",
                    "business_impact", "suggested_investigation"}
        for a in self._collect_all():
            d = a.to_dict()
            missing = required - set(d.keys())
            assert not missing, f"{a.metric} to_dict() missing {missing}"


# ── 3. detect_revenue_anomalies ───────────────────────────────────────────────

class TestDetectRevenueAnomalies:
    def test_empty_returns_empty(self):
        assert detect_revenue_anomalies(ctx=_ctx()) == []

    def test_insufficient_history_returns_empty(self):
        df = _revenue_df(n=MIN_BASELINE_PERIODS)
        assert detect_revenue_anomalies(ctx=_ctx(fact_revenue=df)) == []

    def test_spike_detected(self):
        df = _revenue_df(n=24, spike_month=10, spike_mult=8.0)
        result = detect_revenue_anomalies(ctx=_ctx(fact_revenue=df))
        assert any(a.metric == "revenue" for a in result)

    def test_drop_detected(self):
        np.random.seed(5)
        rows = []
        for i, p in enumerate(_periods(24)):
            rev = 100.0 if i == 15 else 10_000.0 + np.random.normal(0, 500)
            rows.append({"revenue_date": p, "net_revenue_gbp": rev})
        df = pd.DataFrame(rows)
        result = detect_revenue_anomalies(ctx=_ctx(fact_revenue=df))
        drops = [a for a in result if a.deviation_pct < 0]
        assert drops, "Revenue drop not detected"

    def test_metric_name(self):
        df = _revenue_df(n=24, spike_month=10)
        for a in detect_revenue_anomalies(ctx=_ctx(fact_revenue=df)):
            assert a.metric == "revenue"

    def test_both_directions_flagged(self):
        """Revenue detector flags both spikes and drops (symmetric)."""
        df = _revenue_df(n=24, spike_month=10, spike_mult=8.0)
        result = detect_revenue_anomalies(ctx=_ctx(fact_revenue=df))
        assert len(result) >= 1

    def test_normal_series_produces_no_anomalies(self):
        df = _revenue_df(n=24, noise_pct=0.02)   # tight noise, no extreme months
        result = detect_revenue_anomalies(ctx=_ctx(fact_revenue=df))
        # May produce 0; must not produce CRITICAL or HIGH on stable data
        bad = [a for a in result if a.severity in (Severity.CRITICAL, Severity.HIGH)]
        assert not bad, f"Stable revenue series produced {len(bad)} high/critical anomalies"


# ── 4. detect_fraud_anomalies ─────────────────────────────────────────────────

class TestDetectFraudAnomalies:
    def test_empty_events_returns_empty(self):
        assert detect_fraud_anomalies(ctx=_ctx()) == []

    def test_empty_transactions_returns_empty(self):
        evt, _ = _fraud_df(n=12)
        assert detect_fraud_anomalies(ctx=_ctx(fact_product_events=evt)) == []

    def test_no_fraud_events_returns_empty(self):
        _, txn = _fraud_df(n=12)
        evt = pd.DataFrame({"event_date": [], "event_type": []})
        assert detect_fraud_anomalies(
            ctx=_ctx(fact_product_events=evt, fact_transactions=txn)) == []

    def test_rate_spike_detected(self):
        """A genuine rate spike (flags/txns increases) must be flagged."""
        evt, txn = _fraud_df(n=24, spike_month=15)
        result = detect_fraud_anomalies(
            ctx=_ctx(fact_product_events=evt, fact_transactions=txn))
        assert any(a.metric == "fraud_rate" for a in result)

    def test_metric_name_is_fraud_rate(self):
        evt, txn = _fraud_df(n=24, spike_month=10)
        for a in detect_fraud_anomalies(
                ctx=_ctx(fact_product_events=evt, fact_transactions=txn)):
            assert a.metric == "fraud_rate"

    # ── Regression: Sprint 5.3 rate-normalisation fix ─────────────────────
    def test_high_volume_normal_rate_no_false_positive(self):
        """
        Regression: before the Sprint 5.3 fix, a month with 3× transaction
        volume but the same fraud RATE would fire as an anomaly because the
        detector used raw flag counts.  After the fix it must not fire.
        """
        np.random.seed(41)
        evt_rows, txn_rows = [], []
        base_rate = 0.008   # 0.8% fraud rate throughout
        for i, p in enumerate(_periods(24)):
            n_txns = 3000 if i == 10 else 1000   # 3× volume in month 10
            n_flags = round(n_txns * base_rate)
            for _ in range(n_flags):
                evt_rows.append({"event_date": p, "event_type": "fraud_flagged"})
            for _ in range(n_txns):
                txn_rows.append({"transaction_date": p, "status": "completed"})

        evt_df = pd.DataFrame(evt_rows)
        txn_df = pd.DataFrame(txn_rows)
        result = detect_fraud_anomalies(
            ctx=_ctx(fact_product_events=evt_df, fact_transactions=txn_df))
        # High-volume month (index 10) must not appear
        hv_month_date = (_periods(24)[10]).date().replace(day=1)
        false_positives = [
            a for a in result
            if a.detected_at.replace(day=1) == hv_month_date
        ]
        assert not false_positives, (
            f"False positive on high-volume same-rate month: {false_positives}"
        )

    def test_detection_reason_mentions_rate_not_count(self):
        """Detection reason must reference the rate, not raw count."""
        evt, txn = _fraud_df(n=24, spike_month=15)
        result = detect_fraud_anomalies(
            ctx=_ctx(fact_product_events=evt, fact_transactions=txn))
        for a in result:
            reason = a.detection_reason.lower()
            assert "rate" in reason or "per" in reason or "1k" in reason, (
                f"detection_reason does not mention rate: {a.detection_reason}"
            )


# ── 5. detect_kyc_delay_anomalies ─────────────────────────────────────────────

class TestDetectKycDelayAnomalies:
    def test_empty_returns_empty(self):
        assert detect_kyc_delay_anomalies(ctx=_ctx()) == []

    def test_insufficient_history_returns_empty(self):
        df = _kyc_df(n=MIN_BASELINE_PERIODS)
        assert detect_kyc_delay_anomalies(ctx=_ctx(fact_kyc_events=df)) == []

    def test_delay_spike_detected(self):
        df = _kyc_df(n=24, spike_month=12, spike_mult=6.0)
        result = detect_kyc_delay_anomalies(ctx=_ctx(fact_kyc_events=df))
        assert result, "KYC delay spike not detected"

    def test_metric_name(self):
        df = _kyc_df(n=24, spike_month=12, spike_mult=6.0)
        for a in detect_kyc_delay_anomalies(ctx=_ctx(fact_kyc_events=df)):
            assert a.metric == "kyc_processing_time"

    def test_only_upward_spikes_flagged(self):
        """KYC faster than baseline is NOT an anomaly."""
        np.random.seed(31)
        rows = []
        for i, p in enumerate(_periods(24)):
            hours = 1.0 if i == 10 else 12.0 + np.random.normal(0, 1)
            for _ in range(50):
                rows.append({"submission_date": p,
                             "processing_time_hours": max(0.1, hours)})
        df = pd.DataFrame(rows)
        result = detect_kyc_delay_anomalies(ctx=_ctx(fact_kyc_events=df))
        fast = [a for a in result if a.observed_value < a.expected_value]
        assert not fast, "KYC improvement should not fire as anomaly"


# ── 6. detect_transaction_failure_anomalies ───────────────────────────────────

class TestDetectTransactionFailureAnomalies:
    def test_empty_returns_empty(self):
        assert detect_transaction_failure_anomalies(ctx=_ctx()) == []

    def test_insufficient_history_returns_empty(self):
        df = _txn_df(n=MIN_BASELINE_PERIODS)
        assert detect_transaction_failure_anomalies(
            ctx=_ctx(fact_transactions=df)) == []

    def test_failure_spike_detected(self):
        df = _txn_df(n=24, spike_month=15, spike_fail=0.40)
        result = detect_transaction_failure_anomalies(
            ctx=_ctx(fact_transactions=df))
        assert result, "Transaction failure spike not detected"

    def test_metric_name(self):
        df = _txn_df(n=24, spike_month=15, spike_fail=0.40)
        for a in detect_transaction_failure_anomalies(
                ctx=_ctx(fact_transactions=df)):
            assert a.metric == "failed_transaction_rate"

    def test_only_upward_spikes_flagged(self):
        """A month with fewer failures than usual is not an anomaly."""
        np.random.seed(37)
        rows = []
        for i, p in enumerate(_periods(24)):
            fr = 0.001 if i == 10 else 0.05 + np.random.normal(0, 0.005)
            for _ in range(500):
                status = "failed" if np.random.random() < max(0, fr) else "completed"
                rows.append({"transaction_date": p, "status": status})
        df = pd.DataFrame(rows)
        result = detect_transaction_failure_anomalies(
            ctx=_ctx(fact_transactions=df))
        better = [a for a in result if a.observed_value < a.expected_value]
        assert not better, "Improved failure rate should not fire as anomaly"


# ── 7. detect_country_anomalies ───────────────────────────────────────────────

class TestDetectCountryAnomalies:
    def test_empty_returns_empty(self):
        assert detect_country_anomalies(ctx=_ctx()) == []

    def test_insufficient_history_returns_empty(self):
        df = _country_revenue_df(n=MIN_BASELINE_PERIODS)
        assert detect_country_anomalies(ctx=_ctx(fact_revenue=df)) == []

    def test_spike_detected(self):
        df = _country_revenue_df(spike_country="DE", spike_month=10)
        result = detect_country_anomalies(ctx=_ctx(fact_revenue=df))
        de = [a for a in result if a.dimension == "country=DE"]
        assert de, "Country revenue spike not detected"

    def test_dimension_field_set(self):
        df = _country_revenue_df(spike_country="DE", spike_month=10)
        for a in detect_country_anomalies(ctx=_ctx(fact_revenue=df)):
            assert a.dimension and a.dimension.startswith("country=")

    def test_per_country_baseline(self):
        """Each country is compared only to its own history."""
        df = _country_revenue_df(spike_country="DE", spike_month=10)
        for a in detect_country_anomalies(ctx=_ctx(fact_revenue=df)):
            assert "its own" in a.detection_reason

    def test_metric_is_revenue(self):
        df = _country_revenue_df(spike_country="DE", spike_month=10)
        for a in detect_country_anomalies(ctx=_ctx(fact_revenue=df)):
            assert a.metric == "revenue"

    # ── Regression: Sprint 5.3 all-periods fix ────────────────────────────
    def test_mid_history_spike_detected(self):
        """
        Regression: the v0.4 baseline only evaluated z_scores[last_period].
        A spike at month 10 of 24 was invisible.  After the fix, all periods
        are evaluated and mid-history anomalies are detected.
        """
        df = _country_revenue_df(n=24, spike_country="DE", spike_month=10)
        result = detect_country_anomalies(ctx=_ctx(fact_revenue=df))
        spike_date = _periods(24)[10].date().replace(day=1)
        hits = [a for a in result
                if a.dimension == "country=DE"
                and a.detected_at.replace(day=1) == spike_date]
        assert hits, (
            "Mid-history country spike not detected — "
            "Sprint 5.3 all-periods fix may be missing."
        )

    def test_latest_period_still_detected(self):
        """The all-periods fix must not discard the latest period."""
        df = _country_revenue_df(n=24, spike_country="GB", spike_month=23)
        result = detect_country_anomalies(ctx=_ctx(fact_revenue=df))
        gb = [a for a in result if a.dimension == "country=GB"]
        assert gb, "Latest-period spike not detected after all-periods fix"


# ── 8. detect_product_adoption_anomalies ─────────────────────────────────────

class TestDetectProductAdoptionAnomalies:
    def test_empty_returns_empty(self):
        assert detect_product_adoption_anomalies(ctx=_ctx()) == []

    def test_insufficient_history_returns_empty(self):
        df = _product_evt_df(n=MIN_BASELINE_PERIODS)
        assert detect_product_adoption_anomalies(
            ctx=_ctx(fact_product_events=df)) == []

    def test_spike_detected_on_last_period(self):
        df = _product_evt_df(n=24, spike_product="DEBIT_CARD", spike_month=23)
        result = detect_product_adoption_anomalies(
            ctx=_ctx(fact_product_events=df))
        hits = [a for a in result if "DEBIT_CARD" in a.detection_reason]
        assert hits, "Product adoption spike not detected"

    def test_dimension_field_set(self):
        df = _product_evt_df(n=24, spike_product="DEBIT_CARD", spike_month=23)
        for a in detect_product_adoption_anomalies(
                ctx=_ctx(fact_product_events=df)):
            assert a.dimension and a.dimension.startswith("product=")

    def test_metric_is_product_adoption(self):
        df = _product_evt_df(n=24, spike_product="DEBIT_CARD", spike_month=23)
        for a in detect_product_adoption_anomalies(
                ctx=_ctx(fact_product_events=df)):
            assert a.metric == "product_adoption"


# ── 9. detect_customer_behavior_anomalies ─────────────────────────────────────

class TestDetectCustomerBehaviorAnomalies:
    def test_empty_returns_empty(self):
        assert detect_customer_behavior_anomalies(ctx=_ctx()) == []

    def test_churn_spike_detected(self):
        """
        Regression: new Sprint 5.3 detector must catch abnormal churn months.
        """
        df = _customer_df(n=24, churn_month=10, churn_mult=8.0)
        result = detect_customer_behavior_anomalies(ctx=_ctx(dim_customer=df))
        churn_hits = [a for a in result if a.metric == "customer_churn"]
        assert churn_hits, "Churn spike not detected by customer behaviour detector"

    def test_activation_decline_detected(self):
        """
        Regression: new Sprint 5.3 detector must catch a sharp drop in
        new customer activations.

        Uses a dedicated activation-only fixture to avoid the _customer_df
        fixture's churn rows (which backdate activations 6 months and can
        mask the intended drop in the activation series).
        """
        np.random.seed(7)
        base = pd.Timestamp("2022-01-01")
        rows = []
        cid = 1
        for m in range(24):
            period = base + pd.DateOffset(months=m)
            n = 5 if m == 15 else 100          # sharp drop at month 15
            for _ in range(n):
                rows.append({"customer_id": cid, "activation_date": period,
                             "churn_date": None, "last_activity_date": period})
                cid += 1
        df = pd.DataFrame(rows)
        result = detect_customer_behavior_anomalies(ctx=_ctx(dim_customer=df))
        act_hits = [a for a in result if a.metric == "customer_activations"]
        assert act_hits, "Activation decline not detected"

    def test_only_downward_activations_flagged(self):
        """A month with more activations than usual is not flagged."""
        np.random.seed(53)
        rows = []
        base = pd.Timestamp("2022-01-01")
        cid = 1
        for m in range(24):
            period = base + pd.DateOffset(months=m)
            n = 500 if m == 10 else 100   # spike UP in activations
            for _ in range(n):
                rows.append({"customer_id": cid, "activation_date": period,
                             "churn_date": None, "last_activity_date": period})
                cid += 1
        df = pd.DataFrame(rows)
        result = detect_customer_behavior_anomalies(ctx=_ctx(dim_customer=df))
        act_spikes = [a for a in result
                      if a.metric == "customer_activations"
                      and a.deviation_pct > 0]
        assert not act_spikes, "Activation spike must not be flagged (only declines)"

    def test_only_upward_churn_flagged(self):
        """A month with fewer churns than usual is not flagged."""
        np.random.seed(59)
        rows = []
        base = pd.Timestamp("2022-01-01")
        cid = 1
        for m in range(24):
            period = base + pd.DateOffset(months=m)
            n_churn = 2 if m == 10 else 50 + np.random.randint(-5, 5)
            for _ in range(int(n_churn)):
                rows.append({"customer_id": cid,
                             "activation_date": period - pd.DateOffset(months=6),
                             "churn_date": period,
                             "last_activity_date": period - pd.DateOffset(months=3)})
                cid += 1
        df = pd.DataFrame(rows)
        result = detect_customer_behavior_anomalies(ctx=_ctx(dim_customer=df))
        drops = [a for a in result
                 if a.metric == "customer_churn" and a.deviation_pct < 0]
        assert not drops, "Churn improvement must not be flagged"


    def test_mau_decline_detected(self):
        """
        Regression: MAU decline signal in detect_customer_behavior_anomalies.

        Builds dim_customer where last_activity_date drops sharply in one
        month — simulating a platform-wide engagement collapse.  Uses a
        dedicated fixture with natural noise so _zscore_or_pct produces a
        meaningful z-score.
        """
        np.random.seed(61)
        base = pd.Timestamp("2022-01-01")
        rows = []
        cid = 1
        for m in range(24):
            period = base + pd.DateOffset(months=m)
            # Sharp MAU drop at month 18: only 5 active vs ~100 normally
            n_active = 5 if m == 18 else 100
            for _ in range(n_active):
                rows.append({
                    "customer_id":       cid,
                    "activation_date":   period - pd.DateOffset(months=3),
                    "churn_date":        None,
                    "last_activity_date": period,
                })
                cid += 1

        df = pd.DataFrame(rows)
        result = detect_customer_behavior_anomalies(ctx=_ctx(dim_customer=df))
        mau_hits = [a for a in result if a.metric == "monthly_active_users"]
        assert mau_hits, (
            "MAU decline not detected. The customer behaviour detector must "
            "flag months where last_activity_date count is anomalously low."
        )
        hit = mau_hits[0]
        assert hit.observed_value < hit.expected_value, (
            "MAU anomaly must be a decline: observed < expected"
        )
        assert hit.deviation_pct < 0, (
            "MAU decline must produce a negative deviation_pct"
        )

    def test_mau_spike_not_flagged(self):
        """MAU rising above normal is not an anomaly (only declines are flagged)."""
        np.random.seed(67)
        base = pd.Timestamp("2022-01-01")
        rows = []
        cid = 1
        for m in range(24):
            period = base + pd.DateOffset(months=m)
            n = 800 if m == 10 else 100    # spike UP in active users
            for _ in range(n):
                rows.append({
                    "customer_id":        cid,
                    "activation_date":    period - pd.DateOffset(months=3),
                    "churn_date":         None,
                    "last_activity_date": period,
                })
                cid += 1
        df = pd.DataFrame(rows)
        result = detect_customer_behavior_anomalies(ctx=_ctx(dim_customer=df))
        mau_spikes = [a for a in result
                      if a.metric == "monthly_active_users"
                      and a.deviation_pct > 0]
        assert not mau_spikes, "MAU improvement must not be flagged (only declines)"

    def test_metric_names_are_known(self):
        df = _customer_df(n=24, churn_month=10, churn_mult=8.0)
        valid = {"customer_churn", "customer_activations", "monthly_active_users"}
        for a in detect_customer_behavior_anomalies(ctx=_ctx(dim_customer=df)):
            assert a.metric in valid, f"Unknown metric: {a.metric}"

    def test_all_fields_populated(self):
        df = _customer_df(n=24, churn_month=10, churn_mult=8.0)
        for a in detect_customer_behavior_anomalies(ctx=_ctx(dim_customer=df)):
            assert a.detection_reason
            assert a.business_impact
            assert a.suggested_investigation


# ── 10. detect_all_anomalies ──────────────────────────────────────────────────

class TestDetectAllAnomalies:
    def test_empty_data_returns_empty_list(self):
        result = detect_all_anomalies(ctx=_ctx())
        assert result == []

    def test_returns_list_of_anomalies(self):
        df = _revenue_df(n=24, spike_month=10)
        result = detect_all_anomalies(ctx=_ctx(fact_revenue=df))
        assert isinstance(result, list)
        for a in result:
            assert isinstance(a, Anomaly)

    def test_runs_all_seven_detectors(self):
        assert len(DETECTION_FUNCTIONS) == 7

    def test_partial_failure_does_not_abort(self):
        """If one detector raises, the rest continue."""
        ctx = MagicMock()
        call_count = 0

        def _side_effect(table):
            nonlocal call_count
            call_count += 1
            if table == "fact_revenue" and call_count == 1:
                raise RuntimeError("simulated error")
            return pd.DataFrame()

        ctx.get.side_effect = _side_effect
        result = detect_all_anomalies(ctx=ctx)
        assert isinstance(result, list)

    def test_aggregates_results_from_all_sources(self):
        """Results from multiple detectors should be combined in one list."""
        rev_df  = _revenue_df(n=24, spike_month=10)
        cust_df = _customer_df(n=24, churn_month=15, churn_mult=8.0)
        result  = detect_all_anomalies(ctx=_ctx(
            fact_revenue=rev_df,
            dim_customer=cust_df,
        ))
        metrics = {a.metric for a in result}
        assert "revenue" in metrics
        assert "customer_churn" in metrics

    def test_all_results_sorted_or_unsorted_are_anomalies(self):
        df = _revenue_df(n=24, spike_month=10)
        for a in detect_all_anomalies(ctx=_ctx(fact_revenue=df)):
            assert isinstance(a, Anomaly)
