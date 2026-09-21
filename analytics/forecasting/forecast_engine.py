"""
Atlas Forecast Engine

Forecasts Revenue, Customer Growth, Premium Growth, Transactions, Churn.

Deliberately uses simple, explainable techniques over complex models —
per the Sprint 5 spec, interpretability matters more than accuracy at
this stage. Two methods are used, chosen per-metric for what is most
defensible to an executive audience:

  - linear_trend: ordinary least squares on the historical monthly series,
    extrapolated forward. Used for cumulative/growth metrics where a
    straight-line trend is the simplest honest description.
  - moving_average: trailing N-period average, used for metrics that are
    noisy or rate-based (churn %) where a trend line overstates confidence.

Every ForecastResult carries an `accuracy_note` in plain language
explaining what the method does and does not capture — this is a hard
requirement, not optional polish, because forecasts shown to executives
without an honesty caveat are actively misleading.
"""

from __future__ import annotations

from datetime import date
from typing import List, Optional

import numpy as np
import pandas as pd
from loguru import logger

from analytics.core.data_context import DataContext, get_data_context
from analytics.core.types import ForecastPoint, ForecastResult
from analytics.kpis.periods import month_bounds, safe_ratio

DEFAULT_HORIZON_MONTHS = 3
MIN_HISTORY_MONTHS = 3  # below this, a forecast is not statistically defensible


def _monthly_series(df: pd.DataFrame, date_col: str, value_col: str,
                    agg: str = "sum") -> pd.DataFrame:
    """Aggregate a fact table to a monthly time series. Returns columns [period, value]."""
    if not len(df):
        return pd.DataFrame(columns=["period", "value"])
    work = df.copy()
    work["period"] = work[date_col].dt.to_period("M")
    if agg == "sum":
        series = work.groupby("period")[value_col].sum()
    elif agg == "count":
        series = work.groupby("period")[value_col].count()
    elif agg == "nunique":
        series = work.groupby("period")[value_col].nunique()
    else:
        raise ValueError(f"Unsupported agg '{agg}'")
    out = series.reset_index()
    out.columns = ["period", "value"]
    out["period"] = out["period"].astype(str)
    return out


def _linear_trend_forecast(history: pd.DataFrame, horizon: int) -> List[ForecastPoint]:
    """
    Fit y = a*x + b via least squares on the historical series, extrapolate
    `horizon` periods forward. Confidence band widens linearly with
    distance from the last observed point — a simple, honest
    representation of growing forecast uncertainty (not a real prediction
    interval, but directionally correct and clearly labelled as such).
    """
    n = len(history)
    x = np.arange(n)
    y = history["value"].values.astype(float)

    if n < 2:
        last_val = float(y[-1]) if n else 0.0
        return [
            ForecastPoint(period=f"+{i+1}", predicted_value=last_val,
                         lower_bound=last_val * 0.8, upper_bound=last_val * 1.2)
            for i in range(horizon)
        ]

    slope, intercept = np.polyfit(x, y, 1)
    residuals = y - (slope * x + intercept)
    residual_std = float(np.std(residuals)) if n > 2 else abs(float(np.mean(y))) * 0.1

    last_period = pd.Period(history["period"].iloc[-1])
    points = []
    for i in range(1, horizon + 1):
        x_future = n - 1 + i
        predicted = slope * x_future + intercept
        # Uncertainty band widens with forecast distance
        band = residual_std * (1 + 0.3 * i)
        period_label = str(last_period + i)
        points.append(ForecastPoint(
            period=period_label,
            predicted_value=round(max(0.0, predicted), 2),
            lower_bound=round(max(0.0, predicted - band), 2),
            upper_bound=round(predicted + band, 2),
        ))
    return points


def _moving_average_forecast(history: pd.DataFrame, horizon: int,
                             window: int = 3) -> List[ForecastPoint]:
    """
    Trailing N-period moving average held flat forward. Appropriate for
    rate-based metrics (churn %) where extrapolating a trend line would
    falsely imply churn trends linearly to zero or infinity.
    """
    n = len(history)
    w = min(window, n) if n else 1
    recent = history["value"].tail(w).values.astype(float) if n else np.array([0.0])
    avg = float(np.mean(recent))
    std = float(np.std(recent)) if len(recent) > 1 else avg * 0.15

    last_period = pd.Period(history["period"].iloc[-1]) if n else pd.Period(date.today(), "M")
    points = []
    for i in range(1, horizon + 1):
        band = std * (1 + 0.2 * i)
        period_label = str(last_period + i)
        points.append(ForecastPoint(
            period=period_label,
            predicted_value=round(max(0.0, avg), 2),
            lower_bound=round(max(0.0, avg - band), 2),
            upper_bound=round(avg + band, 2),
        ))
    return points


def _accuracy_note(method: str, n_history: int) -> str:
    if n_history < MIN_HISTORY_MONTHS:
        return (
            f"LOW CONFIDENCE: only {n_history} historical period(s) available "
            f"(minimum {MIN_HISTORY_MONTHS} recommended). Forecast should be "
            f"treated as a rough directional estimate only."
        )
    if method == "linear_trend":
        return (
            f"Linear trend fitted on {n_history} historical months. Captures "
            f"the overall growth direction but will not anticipate seasonality, "
            f"one-off events, or trend inflection points. Confidence band widens "
            f"with forecast distance to reflect growing uncertainty."
        )
    return (
        f"Trailing moving-average of the most recent periods, held flat "
        f"forward. Appropriate for rate metrics where a straight-line trend "
        f"would be misleading; will lag behind genuine regime changes."
    )


def forecast_revenue(ctx: Optional[DataContext] = None,
                     horizon_months: int = DEFAULT_HORIZON_MONTHS) -> ForecastResult:
    """Forecast Total Revenue (GBP) using linear trend on monthly net revenue."""
    ctx = ctx or get_data_context()
    rev = ctx.get("fact_revenue")
    history = _monthly_series(rev, "revenue_date", "net_revenue_gbp", agg="sum")

    points = _linear_trend_forecast(history, horizon_months)
    return ForecastResult(
        metric="revenue", method="linear_trend",
        historical=[{"period": r.period, "actual": round(r.value, 2)}
                   for r in history.itertuples(index=False)],
        forecast=points,
        accuracy_note=_accuracy_note("linear_trend", len(history)),
    )


def forecast_customer_growth(ctx: Optional[DataContext] = None,
                             horizon_months: int = DEFAULT_HORIZON_MONTHS) -> ForecastResult:
    """Forecast new customer registrations per month using linear trend."""
    ctx = ctx or get_data_context()
    cust = ctx.get("dim_customer")
    history = _monthly_series(cust, "signup_date", "customer_id", agg="count")

    points = _linear_trend_forecast(history, horizon_months)
    return ForecastResult(
        metric="customer_growth", method="linear_trend",
        historical=[{"period": r.period, "actual": round(r.value, 0)}
                   for r in history.itertuples(index=False)],
        forecast=points,
        accuracy_note=_accuracy_note("linear_trend", len(history)),
    )


def forecast_premium_growth(ctx: Optional[DataContext] = None,
                            horizon_months: int = DEFAULT_HORIZON_MONTHS) -> ForecastResult:
    """Forecast cumulative premium customer count using linear trend on premium_upgrade_date."""
    ctx = ctx or get_data_context()
    cust = ctx.get("dim_customer")
    premium = cust[cust["premium_status"] == True].copy()
    monthly_new = _monthly_series(premium, "premium_upgrade_date", "customer_id", agg="count")

    # Cumulative premium base, not monthly new — more meaningful for "premium growth"
    monthly_new = monthly_new.sort_values("period")
    monthly_new["value"] = monthly_new["value"].cumsum()

    points = _linear_trend_forecast(monthly_new, horizon_months)
    return ForecastResult(
        metric="premium_growth", method="linear_trend",
        historical=[{"period": r.period, "actual": round(r.value, 0)}
                   for r in monthly_new.itertuples(index=False)],
        forecast=points,
        accuracy_note=_accuracy_note("linear_trend", len(monthly_new)),
    )


def forecast_transactions(ctx: Optional[DataContext] = None,
                          horizon_months: int = DEFAULT_HORIZON_MONTHS) -> ForecastResult:
    """Forecast monthly transaction volume using linear trend."""
    ctx = ctx or get_data_context()
    txn = ctx.get("fact_transactions")
    completed = txn[txn["status"] == "completed"] if len(txn) else txn
    history = _monthly_series(completed, "transaction_date", "customer_id", agg="count")

    points = _linear_trend_forecast(history, horizon_months)
    return ForecastResult(
        metric="transactions", method="linear_trend",
        historical=[{"period": r.period, "actual": round(r.value, 0)}
                   for r in history.itertuples(index=False)],
        forecast=points,
        accuracy_note=_accuracy_note("linear_trend", len(history)),
    )


def forecast_churn(ctx: Optional[DataContext] = None,
                   horizon_months: int = DEFAULT_HORIZON_MONTHS) -> ForecastResult:
    """
    Forecast monthly churn rate (%) using a trailing 3-month moving average.
    Moving average (not linear trend) is deliberately used here — churn
    rate is a bounded percentage, and extrapolating a trend line risks
    forecasting negative or runaway values that have no business meaning.
    """
    ctx = ctx or get_data_context()
    cust = ctx.get("dim_customer")

    if not len(cust):
        return ForecastResult(
            metric="churn", method="moving_average", historical=[],
            forecast=[], accuracy_note="No customer data available.",
        )

    churned = cust[cust["churn_date"].notna()].copy()
    monthly_churned = _monthly_series(churned, "churn_date", "customer_id", agg="count")

    # Approximate active base per month for rate calculation
    activated = cust[cust["activation_date"].notna()].copy()
    monthly_active = _monthly_series(activated, "activation_date", "customer_id", agg="count")
    monthly_active = monthly_active.sort_values("period")
    monthly_active["cumulative_base"] = monthly_active["value"].cumsum()

    merged = monthly_churned.merge(
        monthly_active[["period", "cumulative_base"]], on="period", how="left"
    )
    merged["cumulative_base"] = merged["cumulative_base"].ffill().fillna(1)
    merged["rate"] = merged.apply(
        lambda r: round(safe_ratio(r["value"], r["cumulative_base"]) * 100, 2), axis=1
    )
    history = merged[["period", "rate"]].rename(columns={"rate": "value"})

    points = _moving_average_forecast(history, horizon_months, window=3)
    return ForecastResult(
        metric="churn", method="moving_average",
        historical=[{"period": r.period, "actual": round(r.value, 2)}
                   for r in history.itertuples(index=False)],
        forecast=points,
        accuracy_note=_accuracy_note("moving_average", len(history)),
    )


FORECAST_FUNCTIONS = {
    "revenue": forecast_revenue,
    "customer_growth": forecast_customer_growth,
    "premium_growth": forecast_premium_growth,
    "transactions": forecast_transactions,
    "churn": forecast_churn,
}


def forecast_all(ctx: Optional[DataContext] = None,
                 horizon_months: int = DEFAULT_HORIZON_MONTHS) -> dict:
    """Run every registered forecast function. Individual failures are logged and skipped."""
    ctx = ctx or get_data_context()
    results = {}
    for name, fn in FORECAST_FUNCTIONS.items():
        try:
            results[name] = fn(ctx=ctx, horizon_months=horizon_months)
        except Exception as e:
            logger.warning(f"[ForecastEngine] '{name}' failed: {e}")
    logger.info(f"[ForecastEngine] {len(results)}/{len(FORECAST_FUNCTIONS)} forecasts succeeded")
    return results
