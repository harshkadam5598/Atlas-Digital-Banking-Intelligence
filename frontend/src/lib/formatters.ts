/**
 * Shared formatters used across all eight Atlas Intelligence Hubs.
 *
 * These moved here from pages/executiveFormatters.ts during the
 * Sprint 7-wide cleanup: despite the old filename, none of these are
 * actually Executive-specific — every hub uses them. The two genuinely
 * Executive-only formatters (formatPercent, formatSignedPercent — the
 * fraction-based ones, since only executive_service.py returns
 * fraction-scaled percent values) stay in pages/executiveFormatters.ts.
 *
 * No formatting behavior changed in this split — every function below
 * is byte-for-byte identical to its pre-cleanup version, including the
 * Operations fraud-rate and Market precision fixes.
 */

const numberFormatter = new Intl.NumberFormat("en-US");

export function formatCount(value: number): string {
  return numberFormatter.format(value);
}

// Every revenue figure in this backend — executive/kpis.revenue_mtd,
// revenue/summary.value, etc. — traces to
// analytics/kpis/revenue_kpis.py's total_revenue(), which sets
// unit="gbp". (Originally hardcoded to USD; fixed during the Revenue
// hub integration, which also silently corrected the Executive KPI
// Summary's Revenue tile.)
const currencyFormatter = new Intl.NumberFormat("en-GB", {
  style: "currency",
  currency: "GBP",
  maximumFractionDigits: 0,
});

export function formatCurrency(value: number): string {
  return currencyFormatter.format(value);
}

const compactCurrencyFormatter = new Intl.NumberFormat("en-GB", {
  style: "currency",
  currency: "GBP",
  notation: "compact",
  maximumFractionDigits: 1,
});

/** Compact form (e.g. "£1.2M") for space-constrained contexts like chart axes. */
export function formatCurrencyCompact(value: number): string {
  return compactCurrencyFormatter.format(value);
}

/** For values already expressed as whole percentage points (e.g. anomaly deviation_pct). */
export function formatSignedPercentPoints(value: number): string {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}

/**
 * Plain (unsigned) whole-percent formatter. Growth's KPI functions
 * (funnel_conversion, activation_rate, stage_conversion_rates) and most
 * other hubs' percent-unit fields return values already scaled to
 * percent (e.g. 42.5 = 42.5%) — unlike executive_service.py, they do
 * not divide by 100 before returning, so formatPercent (which
 * multiplies by 100) would be wrong here.
 */
export function formatPercentPoints(value: number): string {
  return `${value.toFixed(1)}%`;
}

/**
 * Genuine precision fix, found during the Operations review: fraud_rate()
 * in operations_kpis.py deliberately rounds to 4 decimals ("round(...,
 * 4)"), not 2 like every other percent-unit Operations KPI — because
 * fraud rates are typically well under 1%. formatPercentPoints'
 * toFixed(1) would collapse a real, non-zero rate like 0.03% down to
 * "0.0%", which reads as "no fraud" when there is some. Used only for
 * fraud_rate; every other percent-unit field keeps formatPercentPoints.
 */
export function formatPercentPointsPrecise(value: number): string {
  return `${value.toFixed(2)}%`;
}

/**
 * Signed, 2-decimal version of formatSignedPercentPoints — for fields
 * the backend rounds to 2 decimals (e.g. market_service.py's
 * geographic_revenue_contribution_pct and
 * country_customer_growth_rate_mom), matching that precision exactly
 * rather than the 1-decimal default.
 */
export function formatSignedPercentPointsPrecise(value: number): string {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

const metricValueFormatter = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 2,
});

/** Generic numeric formatting for metric values whose unit varies (rate, count, currency). */
export function formatMetricValue(value: number): string {
  return metricValueFormatter.format(value);
}

/** For backend fields with unit="ratio" (e.g. LTV/CAC ratio). */
export function formatRatio(value: number): string {
  return `${value.toFixed(1)}x`;
}

/**
 * For a plain 0–1 style ratio (e.g. product stickiness = DAU/MAU) where
 * an "x" multiplier suffix would misleadingly imply a different kind of
 * number. No unit suffix — the label/axis/tooltip context carries that.
 */
export function formatRatioValue(value: number): string {
  return value.toFixed(2);
}

/** For backend fields with unit="hours" (e.g. KYC processing time, support resolution time). */
export function formatHours(value: number): string {
  return `${value.toFixed(1)}h`;
}

/** For backend fields with unit="score" on a documented 1–5 scale (e.g. CSAT). */
export function formatScoreOutOfFive(value: number): string {
  return `${value.toFixed(1)} / 5`;
}
