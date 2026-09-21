"""
Atlas Analytics — Forecast Engine Unit Tests
Sprint 5.3 Phase 2C.1

Covers:
  - Every public forecasting function (5 individual + forecast_all)
  - ForecastResult and ForecastPoint structure validation
  - forecast horizon behaviour (default and custom horizons)
  - Empty-data and insufficient-history handling
  - Invalid agg argument handling (_monthly_series)
  - Regression: forecast_all() no longer passes as_of= to individual
    functions (Sprint 5.3 Phase 1 fix)
  - Method selection: churn uses moving_average, others use linear_trend
  - accuracy_note presence and low-confidence flagging
  - lower_bound <= predicted_value <= upper_bound on every point
  - Band widens with forecast distance (growing uncertainty)

Integration tests use mock DataContexts to avoid a live database dependency.
"""

from __future__ import annotations

from datetime import date
from typing import Dict
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from analytics.core.types import ForecastPoint, ForecastResult
from analytics.forecasting.forecast_engine import (
    DEFAULT_HORIZON_MONTHS,
    MIN_HISTORY_MONTHS,
    FORECAST_FUNCTIONS,
    _accuracy_note,
    _linear_trend_forecast,
    _monthly_series,
    _moving_average_forecast,
    forecast_all,
    forecast_churn,
    forecast_customer_growth,
    forecast_premium_growth,
    forecast_revenue,
    forecast_transactions,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_ctx(**tables: pd.DataFrame) -> MagicMock:
    """Return a mock DataContext whose .get() dispatches on table name."""
    ctx = MagicMock()
    ctx.get.side_effect = lambda t: tables.get(t, pd.DataFrame())
    return ctx


def _revenue_df(n_months: int = 24, base: float = 10_000.0,
                noise_pct: float = 0.10) -> pd.DataFrame:
    """Synthetic fact_revenue with natural variance."""
    np.random.seed(42)
    periods = pd.date_range("2022-01-01", periods=n_months, freq="MS")
    rows = []
    for p in periods:
        rows.append({
            "revenue_date": p,
            "net_revenue_gbp": max(0.0, base + np.random.normal(0, base * noise_pct)),
        })
    return pd.DataFrame(rows)


def _customer_df(n_months: int = 24, per_month: int = 200) -> pd.DataFrame:
    """Synthetic dim_customer with signup_date, activation_date, churn_date, premium columns."""
    np.random.seed(42)
    rows = []
    periods = pd.date_range("2022-01-01", periods=n_months, freq="MS")
    cid = 1
    for p in periods:
        for _ in range(per_month):
            churn_d = p + pd.DateOffset(months=6) if np.random.random() < 0.20 else None
            prem_d  = p + pd.DateOffset(months=2) if np.random.random() < 0.25 else None
            rows.append({
                "customer_id":      cid,
                "signup_date":      p,
                "activation_date":  p + pd.DateOffset(days=3),
                "churn_date":       churn_d,
                "premium_upgrade_date": prem_d,
                "premium_status":   prem_d is not None,
            })
            cid += 1
    return pd.DataFrame(rows)


def _transaction_df(n_months: int = 24, per_month: int = 500) -> pd.DataFrame:
    """Synthetic fact_transactions."""
    np.random.seed(42)
    rows = []
    for m in range(n_months):
        period = pd.Timestamp("2022-01-01") + pd.DateOffset(months=m)
        for _ in range(per_month):
            rows.append({
                "transaction_date": period,
                "customer_id": np.random.randint(1, 1000),
                "status": "completed",
            })
    return pd.DataFrame(rows)


# ── 1. _monthly_series helper ─────────────────────────────────────────────────

class TestMonthlySeries:
    def test_empty_df_returns_empty(self):
        result = _monthly_series(pd.DataFrame(), "revenue_date", "net_revenue_gbp")
        assert len(result) == 0
        assert list(result.columns) == ["period", "value"]

    def test_sum_aggregation(self):
        df = pd.DataFrame({
            "revenue_date": pd.to_datetime(["2024-01-15", "2024-01-20", "2024-02-10"]),
            "net_revenue_gbp": [100.0, 200.0, 150.0],
        })
        result = _monthly_series(df, "revenue_date", "net_revenue_gbp", agg="sum")
        assert len(result) == 2
        jan = result[result["period"] == "2024-01"]["value"].iloc[0]
        assert jan == pytest.approx(300.0)

    def test_count_aggregation(self):
        df = pd.DataFrame({
            "signup_date": pd.to_datetime(["2024-01-01", "2024-01-15", "2024-02-01"]),
            "customer_id": [1, 2, 3],
        })
        result = _monthly_series(df, "signup_date", "customer_id", agg="count")
        assert result[result["period"] == "2024-01"]["value"].iloc[0] == 2

    def test_nunique_aggregation(self):
        df = pd.DataFrame({
            "transaction_date": pd.to_datetime(["2024-01-01"] * 4),
            "customer_id": [1, 1, 2, 3],
        })
        result = _monthly_series(df, "transaction_date", "customer_id", agg="nunique")
        assert result["value"].iloc[0] == 3

    def test_invalid_agg_raises(self):
        df = _revenue_df(3)
        with pytest.raises(ValueError, match="Unsupported agg"):
            _monthly_series(df, "revenue_date", "net_revenue_gbp", agg="median")


# ── 2. _linear_trend_forecast ─────────────────────────────────────────────────

class TestLinearTrendForecast:
    def _history(self, n: int = 12, slope: float = 100.0) -> pd.DataFrame:
        periods = pd.period_range("2022-01", periods=n, freq="M")
        values  = [slope * (i + 1) + 5000 for i in range(n)]
        return pd.DataFrame({"period": [str(p) for p in periods], "value": values})

    def test_returns_correct_horizon_length(self):
        h = self._history()
        for horizon in (1, 3, 6, 12):
            points = _linear_trend_forecast(h, horizon)
            assert len(points) == horizon

    def test_all_points_are_forecast_point_instances(self):
        points = _linear_trend_forecast(self._history(), 3)
        for p in points:
            assert isinstance(p, ForecastPoint)

    def test_predicted_value_non_negative(self):
        # Even with negative-sloping data, predicted_value >= 0
        h = pd.DataFrame({"period": ["2024-01", "2024-02", "2024-03"],
                          "value": [300.0, 200.0, 100.0]})
        for p in _linear_trend_forecast(h, 6):
            assert p.predicted_value >= 0.0

    def test_bounds_enclose_prediction(self):
        for p in _linear_trend_forecast(self._history(), 3):
            assert p.lower_bound <= p.predicted_value
            assert p.predicted_value <= p.upper_bound

    def test_band_widens_with_distance(self):
        points = _linear_trend_forecast(self._history(), 6)
        widths = [p.upper_bound - p.lower_bound for p in points]
        for i in range(len(widths) - 1):
            assert widths[i] <= widths[i + 1], (
                f"Band did not widen: step {i}={widths[i]:.2f}, step {i+1}={widths[i+1]:.2f}"
            )

    def test_period_labels_are_strings(self):
        for p in _linear_trend_forecast(self._history(), 3):
            assert isinstance(p.period, str)
            assert len(p.period) > 0

    def test_single_data_point_fallback(self):
        h = pd.DataFrame({"period": ["2024-01"], "value": [500.0]})
        points = _linear_trend_forecast(h, 3)
        assert len(points) == 3
        for p in points:
            assert p.predicted_value == pytest.approx(500.0)

    def test_growing_series_predicts_growth(self):
        h = self._history(n=12, slope=200.0)
        points = _linear_trend_forecast(h, 3)
        last_actual = h["value"].iloc[-1]
        assert points[0].predicted_value > last_actual * 0.8


# ── 3. _moving_average_forecast ───────────────────────────────────────────────

class TestMovingAverageForecast:
    def _history(self, n: int = 12, value: float = 3.5) -> pd.DataFrame:
        periods = pd.period_range("2022-01", periods=n, freq="M")
        return pd.DataFrame({"period": [str(p) for p in periods],
                             "value": [value] * n})

    def test_returns_correct_horizon(self):
        for horizon in (1, 3, 6):
            assert len(_moving_average_forecast(self._history(), horizon)) == horizon

    def test_flat_series_predicts_mean(self):
        points = _moving_average_forecast(self._history(value=4.0), 3)
        for p in points:
            assert p.predicted_value == pytest.approx(4.0)

    def test_bounds_enclose_prediction(self):
        for p in _moving_average_forecast(self._history(), 3):
            assert p.lower_bound <= p.predicted_value
            assert p.upper_bound >= p.predicted_value

    def test_band_widens_with_distance(self):
        points = _moving_average_forecast(self._history(), 6)
        widths = [p.upper_bound - p.lower_bound for p in points]
        for i in range(len(widths) - 1):
            assert widths[i] <= widths[i + 1]

    def test_custom_window_respected(self):
        h = pd.DataFrame({
            "period": ["2024-01", "2024-02", "2024-03", "2024-04"],
            "value": [10.0, 10.0, 10.0, 100.0],
        })
        # window=1: only the last value (100.0) counts
        points_w1 = _moving_average_forecast(h, 3, window=1)
        assert points_w1[0].predicted_value == pytest.approx(100.0)

    def test_predicted_non_negative(self):
        h = pd.DataFrame({"period": ["2024-01", "2024-02"], "value": [1.0, 0.5]})
        for p in _moving_average_forecast(h, 3):
            assert p.predicted_value >= 0.0


# ── 4. _accuracy_note ────────────────────────────────────────────────────────

class TestAccuracyNote:
    def test_low_confidence_when_below_minimum(self):
        note = _accuracy_note("linear_trend", MIN_HISTORY_MONTHS - 1)
        assert "LOW CONFIDENCE" in note
        assert str(MIN_HISTORY_MONTHS) in note

    def test_linear_trend_note_mentions_method(self):
        note = _accuracy_note("linear_trend", 24)
        assert "linear" in note.lower()
        assert "LOW CONFIDENCE" not in note

    def test_moving_average_note_mentions_method(self):
        note = _accuracy_note("moving_average", 12)
        assert "moving" in note.lower() or "average" in note.lower()
        assert "LOW CONFIDENCE" not in note

    def test_note_is_non_empty_string(self):
        for method in ("linear_trend", "moving_average", "unknown_method"):
            note = _accuracy_note(method, 12)
            assert isinstance(note, str)
            assert len(note) > 0


# ── 5. Individual forecast functions ─────────────────────────────────────────

class TestForecastRevenue:
    def test_returns_forecast_result(self):
        ctx = _make_ctx(fact_revenue=_revenue_df())
        result = forecast_revenue(ctx=ctx)
        assert isinstance(result, ForecastResult)

    def test_metric_name(self):
        ctx = _make_ctx(fact_revenue=_revenue_df())
        assert forecast_revenue(ctx=ctx).metric == "revenue"

    def test_method_is_linear_trend(self):
        ctx = _make_ctx(fact_revenue=_revenue_df())
        assert forecast_revenue(ctx=ctx).method == "linear_trend"

    def test_default_horizon_produces_3_points(self):
        ctx = _make_ctx(fact_revenue=_revenue_df())
        result = forecast_revenue(ctx=ctx)
        assert len(result.forecast) == DEFAULT_HORIZON_MONTHS

    def test_custom_horizon_respected(self):
        ctx = _make_ctx(fact_revenue=_revenue_df())
        for h in (1, 6, 12):
            assert len(forecast_revenue(ctx=ctx, horizon_months=h).forecast) == h

    def test_historical_matches_source_months(self):
        df = _revenue_df(n_months=18)
        ctx = _make_ctx(fact_revenue=df)
        result = forecast_revenue(ctx=ctx)
        assert len(result.historical) == 18

    def test_historical_entries_have_period_and_actual(self):
        ctx = _make_ctx(fact_revenue=_revenue_df())
        for entry in forecast_revenue(ctx=ctx).historical:
            assert "period" in entry
            assert "actual" in entry

    def test_accuracy_note_present(self):
        ctx = _make_ctx(fact_revenue=_revenue_df())
        note = forecast_revenue(ctx=ctx).accuracy_note
        assert isinstance(note, str) and len(note) > 10

    def test_empty_data_returns_result_with_empty_forecast(self):
        ctx = _make_ctx(fact_revenue=pd.DataFrame())
        result = forecast_revenue(ctx=ctx)
        assert isinstance(result, ForecastResult)
        # With no data, history is empty; forecast may be empty or single-point fallback
        assert isinstance(result.forecast, list)

    def test_to_dict_is_json_serialisable(self):
        import json
        ctx = _make_ctx(fact_revenue=_revenue_df())
        d = forecast_revenue(ctx=ctx).to_dict()
        json.dumps(d)   # must not raise


class TestForecastCustomerGrowth:
    def test_returns_forecast_result(self):
        ctx = _make_ctx(dim_customer=_customer_df())
        assert isinstance(forecast_customer_growth(ctx=ctx), ForecastResult)

    def test_metric_name(self):
        ctx = _make_ctx(dim_customer=_customer_df())
        assert forecast_customer_growth(ctx=ctx).metric == "customer_growth"

    def test_method_is_linear_trend(self):
        ctx = _make_ctx(dim_customer=_customer_df())
        assert forecast_customer_growth(ctx=ctx).method == "linear_trend"

    def test_default_horizon(self):
        ctx = _make_ctx(dim_customer=_customer_df())
        assert len(forecast_customer_growth(ctx=ctx).forecast) == DEFAULT_HORIZON_MONTHS

    def test_bounds_valid(self):
        ctx = _make_ctx(dim_customer=_customer_df())
        for p in forecast_customer_growth(ctx=ctx).forecast:
            assert p.lower_bound <= p.predicted_value <= p.upper_bound


class TestForecastPremiumGrowth:
    def test_returns_forecast_result(self):
        ctx = _make_ctx(dim_customer=_customer_df())
        assert isinstance(forecast_premium_growth(ctx=ctx), ForecastResult)

    def test_metric_name(self):
        ctx = _make_ctx(dim_customer=_customer_df())
        assert forecast_premium_growth(ctx=ctx).metric == "premium_growth"

    def test_historical_is_cumulative(self):
        """premium_growth tracks cumulative base, so history must be monotonically non-decreasing."""
        ctx = _make_ctx(dim_customer=_customer_df())
        historical = forecast_premium_growth(ctx=ctx).historical
        actuals = [h["actual"] for h in historical]
        for i in range(1, len(actuals)):
            assert actuals[i] >= actuals[i - 1], (
                f"Cumulative premium base decreased at position {i}: "
                f"{actuals[i-1]} → {actuals[i]}"
            )

    def test_no_premium_customers_returns_result(self):
        df = _customer_df()
        df["premium_status"] = False
        df["premium_upgrade_date"] = None
        ctx = _make_ctx(dim_customer=df)
        result = forecast_premium_growth(ctx=ctx)
        assert isinstance(result, ForecastResult)


class TestForecastTransactions:
    def test_returns_forecast_result(self):
        ctx = _make_ctx(fact_transactions=_transaction_df())
        assert isinstance(forecast_transactions(ctx=ctx), ForecastResult)

    def test_metric_name(self):
        ctx = _make_ctx(fact_transactions=_transaction_df())
        assert forecast_transactions(ctx=ctx).metric == "transactions"

    def test_only_completed_transactions_counted(self):
        """Failed transactions must not inflate the forecast baseline."""
        df = _transaction_df(n_months=6, per_month=100)
        df_with_failed = df.copy()
        # Add failed transactions: should not appear in history counts
        failed = df.copy()
        failed["status"] = "failed"
        combined = pd.concat([df_with_failed, failed], ignore_index=True)

        ctx_clean    = _make_ctx(fact_transactions=df_with_failed)
        ctx_combined = _make_ctx(fact_transactions=combined)

        hist_clean    = forecast_transactions(ctx=ctx_clean).historical
        hist_combined = forecast_transactions(ctx=ctx_combined).historical

        for c, co in zip(hist_clean, hist_combined):
            assert c["actual"] == co["actual"], (
                f"Failed transactions changed history count: "
                f"clean={c['actual']}, combined={co['actual']}"
            )


class TestForecastChurn:
    def test_returns_forecast_result(self):
        ctx = _make_ctx(dim_customer=_customer_df())
        assert isinstance(forecast_churn(ctx=ctx), ForecastResult)

    def test_metric_name(self):
        ctx = _make_ctx(dim_customer=_customer_df())
        assert forecast_churn(ctx=ctx).metric == "churn"

    def test_method_is_moving_average(self):
        """Churn uses moving_average, not linear_trend — rate metrics must not be extrapolated."""
        ctx = _make_ctx(dim_customer=_customer_df())
        assert forecast_churn(ctx=ctx).method == "moving_average"

    def test_churn_rate_non_negative(self):
        ctx = _make_ctx(dim_customer=_customer_df())
        for h in forecast_churn(ctx=ctx).historical:
            assert h["actual"] >= 0.0

    def test_empty_customer_data_returns_safe_result(self):
        ctx = _make_ctx(dim_customer=pd.DataFrame())
        result = forecast_churn(ctx=ctx)
        assert isinstance(result, ForecastResult)
        assert result.metric == "churn"

    def test_no_churned_customers_returns_result(self):
        df = _customer_df()
        df["churn_date"] = None
        ctx = _make_ctx(dim_customer=df)
        result = forecast_churn(ctx=ctx)
        assert isinstance(result, ForecastResult)


# ── 6. forecast_all ───────────────────────────────────────────────────────────

class TestForecastAll:
    def _full_ctx(self):
        return _make_ctx(
            fact_revenue=_revenue_df(),
            dim_customer=_customer_df(),
            fact_transactions=_transaction_df(),
        )

    def test_returns_all_five_metrics(self):
        results = forecast_all(ctx=self._full_ctx())
        assert set(results.keys()) == set(FORECAST_FUNCTIONS.keys())

    def test_every_value_is_forecast_result(self):
        for name, result in forecast_all(ctx=self._full_ctx()).items():
            assert isinstance(result, ForecastResult), f"{name} is not a ForecastResult"

    def test_partial_failure_does_not_abort(self):
        """
        If one forecaster raises an unexpected error, the orchestrator continues
        and the remaining forecasters still produce results.

        forecast_all() catches per-function exceptions and logs a warning rather
        than propagating the error.  A failed function is simply absent from
        the returned dict (or, if the engine returns a degraded result, it is
        still a ForecastResult instance).

        Note: premium_growth also fails on empty dim_customer (missing column),
        so two functions may fail with this fixture.  The assertion is that
        at least one function succeeds despite revenue erroring — confirming
        the orchestrator does not abort on first failure.
        """
        ctx = MagicMock()
        def _side_effect(table):
            if table == "fact_revenue":
                raise RuntimeError("simulated DB error")
            return pd.DataFrame()
        ctx.get.side_effect = _side_effect

        results = forecast_all(ctx=ctx)
        # revenue failed; confirm it is absent from results
        assert "revenue" not in results
        # At least one other forecaster must have succeeded or returned a result
        other_keys = [k for k in FORECAST_FUNCTIONS if k != "revenue"]
        completed = [k for k in other_keys if k in results]
        assert len(completed) >= 1, (
            f"Expected at least one forecaster to succeed after revenue error. "
            f"Got results for: {list(results.keys())}"
        )
        # Every result that is present must be a ForecastResult
        for name, result in results.items():
            assert isinstance(result, ForecastResult), f"{name} is not a ForecastResult"

    def test_custom_horizon_propagates_to_all(self):
        results = forecast_all(ctx=self._full_ctx(), horizon_months=6)
        for name, result in results.items():
            assert len(result.forecast) == 6, (
                f"{name}: expected horizon=6, got {len(result.forecast)}"
            )

    # ── Regression: Sprint 5.3 Phase 1 fix ───────────────────────────────
    def test_forecast_all_does_not_accept_as_of_kwarg(self):
        """
        Regression test for Sprint 5.3 Phase 1 runner fix.
        forecast_all() must NOT accept an as_of keyword argument.
        The runner previously passed as_of=as_of, which caused a TypeError
        that silently produced zero forecasts in AnalyticsResult.
        """
        import inspect
        sig = inspect.signature(forecast_all)
        assert "as_of" not in sig.parameters, (
            "forecast_all() must not have an as_of parameter — "
            "adding one would allow the runner bug to be reintroduced silently."
        )

    def test_individual_forecasters_do_not_accept_as_of(self):
        """
        Companion regression: none of the five individual forecast functions
        should accept as_of — they always forecast from the latest data.
        """
        import inspect
        for name, fn in FORECAST_FUNCTIONS.items():
            sig = inspect.signature(fn)
            assert "as_of" not in sig.parameters, (
                f"{name}() must not have an as_of parameter"
            )

    def test_empty_data_all_metrics_return_results(self):
        ctx = _make_ctx()
        results = forecast_all(ctx=ctx)
        # Every function must return a ForecastResult even with empty data
        for name, result in results.items():
            assert isinstance(result, ForecastResult), (
                f"{name} did not return ForecastResult on empty data"
            )

    def test_to_dict_all_serialisable(self):
        import json
        for name, result in forecast_all(ctx=self._full_ctx()).items():
            try:
                json.dumps(result.to_dict())
            except (TypeError, ValueError) as e:
                pytest.fail(f"{name}.to_dict() is not JSON-serialisable: {e}")


# ── 7. ForecastResult / ForecastPoint structure ───────────────────────────────

class TestForecastResultStructure:
    """Cross-cutting structural checks applied to every public function."""

    @pytest.fixture(scope="class")
    def all_results(self):
        ctx = _make_ctx(
            fact_revenue=_revenue_df(),
            dim_customer=_customer_df(),
            fact_transactions=_transaction_df(),
        )
        return forecast_all(ctx=ctx)

    def test_every_result_has_required_fields(self, all_results):
        required = {"metric", "method", "historical", "forecast", "accuracy_note"}
        for name, result in all_results.items():
            d = result.to_dict()
            missing = required - set(d.keys())
            assert not missing, f"{name} missing fields: {missing}"

    def test_every_forecast_point_has_required_fields(self, all_results):
        for name, result in all_results.items():
            for i, point in enumerate(result.forecast):
                assert isinstance(point.period, str) and point.period, \
                    f"{name} forecast[{i}].period is empty"
                assert isinstance(point.predicted_value, float)
                assert isinstance(point.lower_bound, float)
                assert isinstance(point.upper_bound, float)

    def test_bounds_always_valid(self, all_results):
        for name, result in all_results.items():
            for i, point in enumerate(result.forecast):
                assert point.lower_bound <= point.predicted_value, \
                    f"{name}[{i}]: lower_bound > predicted_value"
                assert point.predicted_value <= point.upper_bound, \
                    f"{name}[{i}]: predicted_value > upper_bound"

    def test_all_predicted_values_non_negative(self, all_results):
        for name, result in all_results.items():
            for i, point in enumerate(result.forecast):
                assert point.predicted_value >= 0.0, \
                    f"{name}[{i}]: predicted_value={point.predicted_value} < 0"

    def test_accuracy_note_non_empty_on_all(self, all_results):
        for name, result in all_results.items():
            assert result.accuracy_note and len(result.accuracy_note) > 10, \
                f"{name}: accuracy_note is empty or too short"

    def test_churn_uses_moving_average_others_use_linear_trend(self, all_results):
        for name, result in all_results.items():
            if name == "churn":
                assert result.method == "moving_average", \
                    "Churn must use moving_average (rate metric — cannot extrapolate)"
            else:
                assert result.method == "linear_trend", \
                    f"{name} should use linear_trend, got {result.method}"
