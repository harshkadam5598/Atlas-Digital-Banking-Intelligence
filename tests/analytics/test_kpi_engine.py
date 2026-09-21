"""
Atlas Analytics — KPI Engine Unit Tests
Verifies every registered KPI computes without error and returns
sane, well-typed values against the Sprint 4 staging dataset.
"""

from datetime import date

import pytest

from analytics.core.data_context import ParquetDataContext
from analytics.core.types import KPIResult
from analytics.kpis.registry import compute, compute_all, list_kpis


@pytest.fixture(scope="module")
def ctx():
    return ParquetDataContext()


def test_registry_has_expected_domains():
    domains = {"customer", "revenue", "product", "operations"}
    all_kpis = list_kpis()
    assert len(all_kpis) >= 22, "Spec requires at least the 22 named KPIs"
    for domain in domains:
        assert len(list_kpis(domain)) > 0, f"No KPIs registered for domain '{domain}'"


def test_unknown_kpi_raises_keyerror(ctx):
    with pytest.raises(KeyError):
        compute("not_a_real_kpi", ctx=ctx)


@pytest.mark.parametrize("name", list_kpis())
def test_every_kpi_computes_without_error(ctx, name):
    result = compute(name, ctx=ctx)
    assert isinstance(result, KPIResult)
    assert result.name == name
    assert isinstance(result.value, float)
    assert result.value == result.value, "value must not be NaN"
    assert result.unit in {"count", "gbp", "percent", "ratio", "days", "hours", "score"}


def test_compute_all_returns_all_registered(ctx):
    results = compute_all(ctx=ctx)
    assert len(results) == len(list_kpis())


def test_percent_kpis_within_bounds(ctx):
    """Percent-unit KPIs should be in [0, 100] for this dataset (no negative rates)."""
    for name in list_kpis():
        result = compute(name, ctx=ctx)
        if result.unit == "percent" and "growth" not in name:
            assert 0.0 <= result.value <= 100.0, f"{name} percent out of bounds: {result.value}"


def test_total_revenue_breakdown_sums_to_total(ctx):
    result = compute("total_revenue", ctx=ctx)
    by_type = result.breakdown.get("by_revenue_type", {})
    if by_type:
        assert abs(sum(by_type.values()) - result.value) < 0.01


def test_kpi_result_delta_computed_when_previous_present():
    r = KPIResult(name="x", value=110.0, unit="gbp", as_of=date(2024, 1, 1), previous_value=100.0)
    assert r.delta == 10.0
    assert r.delta_pct == 10.0
    assert r.trend.value == "up"


def test_kpi_result_no_delta_without_previous():
    r = KPIResult(name="x", value=110.0, unit="gbp", as_of=date(2024, 1, 1))
    assert r.delta is None
    assert r.trend is None


def test_arpu_is_revenue_divided_by_mau(ctx):
    from analytics.kpis.revenue_kpis import arpu, total_revenue
    from analytics.kpis.customer_kpis import monthly_active_users

    arpu_result = arpu(ctx=ctx)
    rev = total_revenue(ctx=ctx)
    mau = monthly_active_users(ctx=ctx)
    expected = round(rev.value / mau.value, 2) if mau.value else 0.0
    assert arpu_result.value == expected
