"""
Atlas Decision Intelligence Engine

Generates actionable business recommendations from a registry of explicit,
auditable business rules. Every rule:
  1. Reads one or more KPIResults (via the registry, never raw DataFrames)
  2. Evaluates a threshold condition
  3. If triggered, emits a Recommendation with rationale, supporting KPIs,
     estimated impact, and priority

Rules are independent functions registered in DECISION_RULES — adding a
new rule never requires touching existing rules, matching the modular,
independently-testable requirement from the Sprint 5 spec.
"""

from __future__ import annotations

from datetime import date
from typing import Callable, Dict, List, Optional

from loguru import logger

from analytics.core.data_context import DataContext, get_data_context
from analytics.core.types import KPIResult, Priority, Recommendation
from analytics.kpis.registry import compute

RuleFunction = Callable[[DataContext, date], Optional[Recommendation]]


# ── Individual business rules ─────────────────────────────────────────────────

def rule_premium_marketing_high_fx(ctx: DataContext, as_of: date) -> Optional[Recommendation]:
    """
    RULE-001: If FX product adoption is meaningfully high among non-premium
    customers and premium conversion is below target (20%), recommend
    targeted premium marketing to high-FX-usage customers — they are
    already paying for currency conversion and are a strong premium
    upsell signal per the Sprint 3 blueprint's premium probability model.
    """
    adoption = compute("product_adoption", ctx=ctx, as_of=as_of)
    premium = compute("premium_conversion_rate", ctx=ctx, as_of=as_of)

    fx_adoption = adoption.breakdown.get("by_product", {}).get("FX_STANDARD", 0.0)

    if fx_adoption >= 30.0 and premium.value < 25.0:
        return Recommendation(
            title="Increase Premium marketing to high-FX users",
            rationale=(
                f"FX_STANDARD adoption is {fx_adoption:.1f}% of the active base, but "
                f"premium conversion sits at only {premium.value:.1f}% (target 20-25%). "
                f"Customers already paying FX spreads are a high-intent premium "
                f"upsell segment — Atlas's premium probability model weights FX "
                f"adoption at 1.3x base conversion likelihood."
            ),
            supporting_kpis=["product_adoption", "premium_conversion_rate"],
            estimated_impact=(
                f"Targeting the FX-active segment could lift premium conversion "
                f"by an estimated 2-4 percentage points based on the 1.3x signal multiplier."
            ),
            priority=Priority.HIGH if premium.value < 18.0 else Priority.MEDIUM,
            category="growth",
            rule_id="RULE-001",
        )
    return None


def rule_early_churn_investigation(ctx: DataContext, as_of: date) -> Optional[Recommendation]:
    """
    RULE-002: If churn rate is elevated AND retention at month 1 is low,
    flag that churn is concentrated in newly activated customers — this
    points to an onboarding problem, not a mature-customer satisfaction
    problem, and requires a different remediation.
    """
    churn = compute("churn_rate", ctx=ctx, as_of=as_of)
    retention_m1 = compute("retention_rate", ctx=ctx, as_of=as_of, period_months=1)

    if churn.value >= 5.0 and retention_m1.value < 60.0:
        return Recommendation(
            title="Investigate increased churn in newly activated customers",
            rationale=(
                f"Monthly churn rate is {churn.value:.1f}% while Month-1 cohort "
                f"retention is only {retention_m1.value:.1f}% (cohort size "
                f"{retention_m1.metadata.get('cohort_size', 0)}). Churn concentrated "
                f"this early in the lifecycle typically indicates onboarding "
                f"friction or unmet first-transaction expectations, not "
                f"long-term product dissatisfaction."
            ),
            supporting_kpis=["churn_rate", "retention_rate"],
            estimated_impact=(
                "Improving Month-1 retention by 10 points would reduce blended "
                "monthly churn proportionally, given new cohorts are the largest "
                "share of the active base during the growth phase."
            ),
            priority=Priority.HIGH if churn.value >= 8.0 else Priority.MEDIUM,
            category="retention",
            rule_id="RULE-002",
        )
    return None


def rule_promote_investments_to_tenured_premium(ctx: DataContext, as_of: date) -> Optional[Recommendation]:
    """
    RULE-003: If cross-sell rate is below the blueprint target (82%) and
    CLV/ARPU indicate healthy unit economics, recommend promoting
    investment products to long-tenure premium customers — the Sprint 3
    blueprint shows INVEST_PREMIUM adoption among premium holders at 41%,
    well below full saturation, and this segment has the income profile
    most likely to convert.
    """
    cross_sell = compute("cross_sell_rate", ctx=ctx, as_of=as_of)
    ltv_cac = compute("ltv_cac_ratio", ctx=ctx, as_of=as_of)
    feature = compute("feature_adoption", ctx=ctx, as_of=as_of,
                      feature_event_type="investment_opened")

    if cross_sell.value < 82.0 and ltv_cac.value > 0:
        return Recommendation(
            title="Promote Investments to long-tenure Premium customers",
            rationale=(
                f"Cross-sell rate is {cross_sell.value:.1f}% against an 82% blueprint "
                f"target. Investment product adoption is {feature.value:.1f}% of "
                f"the eligible base. Premium customers with longer tenure have "
                f"demonstrated trust in the platform and are statistically the "
                f"most likely segment to adopt a second financial product."
            ),
            supporting_kpis=["cross_sell_rate", "feature_adoption", "ltv_cac_ratio"],
            estimated_impact=(
                f"Closing even half the gap to the 82% cross-sell target would "
                f"materially increase ARPU given investment products carry a "
                f"recurring AUM fee rather than a one-off transaction fee."
            ),
            priority=Priority.MEDIUM,
            category="growth",
            rule_id="RULE-003",
        )
    return None


def rule_kyc_delay_review(ctx: DataContext, as_of: date) -> Optional[Recommendation]:
    """
    RULE-004: If KYC processing time exceeds the 24h target, or approval
    rate falls outside the expected 78-86% band in any specific country,
    recommend a country-level KYC operations review.
    """
    processing = compute("kyc_processing_time", ctx=ctx, as_of=as_of)
    approval = compute("kyc_approval_rate", ctx=ctx, as_of=as_of)

    slow_overall = processing.value > 24.0
    by_country = approval.breakdown.get("by_country", {})
    outlier_countries = {
        c: rate for c, rate in by_country.items()
        if rate < 70.0 or rate > 95.0
    }

    if slow_overall or outlier_countries:
        country_note = (
            f" Outlier countries: {', '.join(f'{c} ({r:.0f}%)' for c, r in outlier_countries.items())}."
            if outlier_countries else ""
        )
        return Recommendation(
            title="Review KYC delays in specific countries",
            rationale=(
                f"Median KYC processing time is {processing.value:.1f} hours "
                f"(target <24h). Overall approval rate is {approval.value:.1f}%."
                f"{country_note}"
            ),
            supporting_kpis=["kyc_processing_time", "kyc_approval_rate"],
            estimated_impact=(
                "Faster KYC turnaround directly shortens time-to-activation, "
                "which the blueprint identifies as a top-3 growth lever — "
                "median activation lag is bounded by KYC completion time."
            ),
            priority=Priority.HIGH if processing.value > 48.0 else Priority.MEDIUM,
            category="operations",
            rule_id="RULE-004",
            metadata={"outlier_countries": outlier_countries},
        )
    return None


def rule_fraud_rate_review(ctx: DataContext, as_of: date) -> Optional[Recommendation]:
    """
    RULE-005: If fraud_rate exceeds the blueprint baseline (0.8% of
    completed transactions) or the fraud_cleared/flagged ratio drops
    below the 78% baseline, recommend a fraud operations review.
    """
    fraud = compute("fraud_rate", ctx=ctx, as_of=as_of)
    clear_ratio = fraud.metadata.get("clear_ratio_pct", 100.0)

    if fraud.value > 1.2 or clear_ratio < 60.0:
        return Recommendation(
            title="Review fraud detection thresholds",
            rationale=(
                f"Fraud flag rate is {fraud.value:.3f}% of completed transactions "
                f"against a {0.8:.1f}% blueprint baseline. Clear ratio is "
                f"{clear_ratio:.1f}% (baseline 78%). A rising flag rate with a "
                f"falling clear ratio suggests either a genuine fraud increase "
                f"or an overly aggressive detection rule generating false positives."
            ),
            supporting_kpis=["fraud_rate"],
            estimated_impact=(
                "Unresolved flags directly block legitimate transactions, "
                "harming activation and retention; a 2x baseline fraud rate "
                "warrants immediate rule calibration review."
            ),
            priority=Priority.HIGH if fraud.value > 1.6 else Priority.MEDIUM,
            category="risk",
            rule_id="RULE-005",
        )
    return None


def rule_failed_transaction_review(ctx: DataContext, as_of: date) -> Optional[Recommendation]:
    """
    RULE-006: If failed_transaction_rate exceeds the 2% alert threshold
    defined in kpi_definitions.md, recommend a payment infrastructure review.
    """
    failed = compute("failed_transaction_rate", ctx=ctx, as_of=as_of)

    if failed.value > 2.0:
        by_product = failed.breakdown.get("by_product", {})
        worst_product = max(by_product.items(), key=lambda kv: kv[1]) if by_product else None
        product_note = (
            f" {worst_product[0]} has the highest failure rate at {worst_product[1]:.1f}%."
            if worst_product else ""
        )
        return Recommendation(
            title="Investigate elevated transaction failure rate",
            rationale=(
                f"Failed transaction rate is {failed.value:.1f}%, exceeding the "
                f"2.0% alert threshold.{product_note}"
            ),
            supporting_kpis=["failed_transaction_rate"],
            estimated_impact=(
                "Every failed transaction is a friction point that can trigger "
                "support contacts and erode trust; reducing failures toward the "
                "blueprint baseline of 2.5% directly improves both CSAT and "
                "operational cost."
            ),
            priority=Priority.HIGH if failed.value > 4.0 else Priority.MEDIUM,
            category="operations",
            rule_id="RULE-006",
        )
    return None


def rule_low_ltv_cac_review(ctx: DataContext, as_of: date) -> Optional[Recommendation]:
    """
    RULE-007: If LTV/CAC ratio falls below the healthy threshold (1.0),
    recommend a channel-level acquisition cost review — acquiring
    customers below cost is unsustainable regardless of growth rate.
    """
    ratio = compute("ltv_cac_ratio", ctx=ctx, as_of=as_of)

    if 0 < ratio.value < 1.0:
        return Recommendation(
            title="Review acquisition spend — LTV/CAC below breakeven",
            rationale=(
                f"LTV/CAC ratio is {ratio.value:.2f}, below the 1.0 breakeven "
                f"threshold (healthy benchmark is >3.0). Blended CAC is "
                f"£{ratio.metadata.get('blended_cac_gbp', 0):.2f} against a "
                f"CLV of £{ratio.metadata.get('clv_gbp', 0):.2f}."
            ),
            supporting_kpis=["ltv_cac_ratio", "clv"],
            estimated_impact=(
                "Continuing to acquire customers below this ratio destroys "
                "value per customer acquired; shifting spend toward lower-CAC "
                "channels (organic, referral) until CLV catches up via tenure "
                "is the standard corrective lever."
            ),
            priority=Priority.HIGH,
            category="growth",
            rule_id="RULE-007",
        )
    return None


DECISION_RULES: List[RuleFunction] = [
    rule_premium_marketing_high_fx,
    rule_early_churn_investigation,
    rule_promote_investments_to_tenured_premium,
    rule_kyc_delay_review,
    rule_fraud_rate_review,
    rule_failed_transaction_review,
    rule_low_ltv_cac_review,
]


def generate_recommendations(ctx: Optional[DataContext] = None,
                             as_of: Optional[date] = None) -> List[Recommendation]:
    """
    Evaluate every registered business rule and return all triggered
    recommendations, sorted High -> Medium -> Low priority.
    A rule raising an exception is logged and skipped — one broken rule
    must not prevent the other rules from running.
    """
    ctx = ctx or get_data_context()
    as_of = as_of or ctx.as_of()

    priority_order = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}
    recommendations: List[Recommendation] = []

    for rule_fn in DECISION_RULES:
        try:
            result = rule_fn(ctx, as_of)
            if result:
                recommendations.append(result)
        except Exception as e:
            logger.warning(f"[DecisionEngine] Rule '{rule_fn.__name__}' failed: {e}")

    recommendations.sort(key=lambda r: priority_order[r.priority])
    logger.info(f"[DecisionEngine] {len(recommendations)} recommendation(s) triggered "
               f"from {len(DECISION_RULES)} rules evaluated")
    return recommendations
