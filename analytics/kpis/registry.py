"""
Atlas KPI Engine — Registry

The reusable KPI calculation framework. Every KPI function across all
four domains (customer, revenue, product, operations) is registered
here under a stable string key, so any other engine (Insight, Decision,
Forecast, Anomaly) can call:

    from analytics.kpis.registry import compute, compute_all
    result = compute("total_revenue", as_of=some_date)
    all_kpis = compute_all(as_of=some_date)

This is the single integration point — no engine should import a KPI
function directly from customer_kpis.py etc. Going through the registry
means every KPI is logged consistently and Sprint 6's API layer can
expose `/api/v1/kpis/{name}` generically without a giant if/elif chain.
"""

from __future__ import annotations

from datetime import date
from typing import Callable, Dict, List, Optional

from loguru import logger

from analytics.core.data_context import DataContext
from analytics.core.types import KPIResult
from analytics.kpis import customer_kpis, growth_kpis, operations_kpis, product_kpis, revenue_kpis

KPIFunction = Callable[..., KPIResult]

_REGISTRY: Dict[str, Dict[str, object]] = {}


def register(name: str, fn: KPIFunction, domain: str, description: str) -> None:
    if name in _REGISTRY:
        raise ValueError(f"KPI '{name}' already registered")
    _REGISTRY[name] = {"fn": fn, "domain": domain, "description": description}


def _build_registry() -> None:
    if _REGISTRY:
        return

    # ── Customer domain ──────────────────────────────────────────────────────
    register("daily_active_users", customer_kpis.daily_active_users,
             "customer", "Distinct customers active on a given day")
    register("weekly_active_users", customer_kpis.weekly_active_users,
             "customer", "Distinct customers active in trailing 7 days")
    register("monthly_active_users", customer_kpis.monthly_active_users,
             "customer", "Distinct customers active in the calendar month")
    register("active_customers", customer_kpis.active_customers,
             "customer", "Point-in-time count of activated/reactivated customers")
    register("new_customers", customer_kpis.new_customers,
             "customer", "Customers who signed up in the calendar month")
    register("returning_customers", customer_kpis.returning_customers,
             "customer", "Customers active this month who were also active last month")
    register("churn_rate", customer_kpis.churn_rate,
             "customer", "Pct of prior-month-active customers with zero activity this month")
    register("retention_rate", customer_kpis.retention_rate,
             "customer", "Pct of a signup cohort still active N periods later")
    register("premium_conversion_rate", customer_kpis.premium_conversion_rate,
             "customer", "Pct of activated customers with premium_status=True")

    # ── Revenue domain ───────────────────────────────────────────────────────
    register("total_revenue", revenue_kpis.total_revenue,
             "revenue", "Total net revenue for the calendar month")
    register("revenue_by_product", revenue_kpis.revenue_by_product,
             "revenue", "Net revenue grouped by product")
    register("revenue_by_country", revenue_kpis.revenue_by_country,
             "revenue", "Net revenue grouped by country")
    register("revenue_by_segment", revenue_kpis.revenue_by_segment,
             "revenue", "Net revenue grouped by customer segment")
    register("arpu", revenue_kpis.arpu,
             "revenue", "Average revenue per active user")
    register("clv", revenue_kpis.clv,
             "revenue", "Customer lifetime value (ARPU x lifespan x margin)")
    register("ltv_cac_ratio", revenue_kpis.ltv_cac_ratio,
             "revenue", "CLV divided by blended customer acquisition cost")
    register("revenue_growth", revenue_kpis.revenue_growth,
             "revenue", "Month-over-month revenue growth percentage")

    # ── Product domain ───────────────────────────────────────────────────────
    register("product_adoption", product_kpis.product_adoption,
             "product", "Pct of active customers who have used each product")
    register("product_stickiness", product_kpis.product_stickiness,
             "product", "DAU/MAU ratio per product")
    register("cross_sell_rate", product_kpis.cross_sell_rate,
             "product", "Pct of active customers holding >=2 products")
    register("feature_adoption", product_kpis.feature_adoption,
             "product", "Pct of eligible customers who used a specific feature")

    # ── Operations domain ────────────────────────────────────────────────────
    register("kyc_approval_rate", operations_kpis.kyc_approval_rate,
             "operations", "Pct of KYC submissions approved")
    register("kyc_processing_time", operations_kpis.kyc_processing_time,
             "operations", "Median KYC processing time in hours")
    register("support_resolution_time", operations_kpis.support_resolution_time,
             "operations", "Average support ticket resolution time in hours")
    register("csat", operations_kpis.csat,
             "operations", "Average customer satisfaction score (1-5)")
    register("fraud_rate", operations_kpis.fraud_rate,
             "operations", "Pct of completed transactions flagged for fraud")
    register("failed_transaction_rate", operations_kpis.failed_transaction_rate,
             "operations", "Pct of transactions with status=failed")

    # ── Growth domain (Sprint 6 approved narrow extension) ──────────────────
    register("funnel_conversion", growth_kpis.funnel_conversion,
             "growth", "Registration-to-first-transaction funnel, by stage")
    register("cac_by_channel", growth_kpis.cac_by_channel,
             "growth", "Customer acquisition cost per marketing channel")
    register("activation_rate", growth_kpis.activation_rate,
             "growth", "Pct of registration cohort transacting within 30 days")


_build_registry()


def list_kpis(domain: Optional[str] = None) -> List[str]:
    """Return all registered KPI names, optionally filtered by domain."""
    if domain:
        return [k for k, v in _REGISTRY.items() if v["domain"] == domain]
    return list(_REGISTRY.keys())


def describe(name: str) -> Dict[str, str]:
    if name not in _REGISTRY:
        raise KeyError(f"Unknown KPI '{name}'. Available: {list_kpis()}")
    return {"name": name, "domain": _REGISTRY[name]["domain"],
            "description": _REGISTRY[name]["description"]}


def compute(name: str, ctx: Optional[DataContext] = None,
           as_of: Optional[date] = None, **kwargs) -> KPIResult:
    """
    Compute a single KPI by registered name.
    Raises KeyError if the name is not registered — fails loudly rather
    than silently returning an empty result for a typo'd KPI name.
    """
    if name not in _REGISTRY:
        raise KeyError(f"Unknown KPI '{name}'. Available: {list_kpis()}")
    fn = _REGISTRY[name]["fn"]
    logger.debug(f"[KPI] computing '{name}' as_of={as_of}")
    try:
        return fn(ctx=ctx, as_of=as_of, **kwargs)
    except Exception as e:
        logger.error(f"[KPI] '{name}' failed: {e}")
        raise


def compute_all(ctx: Optional[DataContext] = None,
                as_of: Optional[date] = None,
                domain: Optional[str] = None) -> Dict[str, KPIResult]:
    """
    Compute every registered KPI (or every KPI in one domain).
    Individual KPI failures are logged and skipped rather than aborting
    the full batch — one broken KPI should not block the other 22.
    """
    names = list_kpis(domain)
    results: Dict[str, KPIResult] = {}
    for name in names:
        try:
            results[name] = compute(name, ctx=ctx, as_of=as_of)
        except Exception as e:
            logger.warning(f"[KPI] Skipping '{name}' in compute_all: {e}")
    logger.info(f"[KPI] compute_all: {len(results)}/{len(names)} succeeded "
               f"(domain={domain or 'all'})")
    return results
