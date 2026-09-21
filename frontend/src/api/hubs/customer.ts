import { apiGet } from "../client";

/**
 * customer_service.get_summary() returns 6 of the customer domain's 9
 * KPIs as raw values (no delta/trend — those come from the underlying
 * KPIResult objects but summary only exposes .value). churn_rate,
 * retention_rate, premium_conversion_rate are already whole-percent
 * (e.g. 4.2 = 4.2%), matching every other customer_kpis.py function.
 */
export interface CustomerSummary {
  active_customers: number;
  new_customers: number;
  returning_customers: number;
  churn_rate: number;
  retention_rate: number;
  premium_conversion_rate: number;
  as_of_date: string;
}

/** GET /api/v1/customer/summary */
export function getCustomerSummary() {
  return apiGet<CustomerSummary>("/api/v1/customer/summary");
}

/** Generic KPIResult.to_dict() shape shared by every customer-domain KPI. */
interface KpiResultBase {
  name: string;
  value: number;
  unit: string;
  as_of: string;
  period_label: string;
  previous_value: number | null;
  delta: number | null;
  delta_pct: number | null;
  trend: "up" | "down" | "flat" | null;
}

export interface ActivityKpi extends KpiResultBase {
  breakdown?: {
    by_country?: Record<string, number>;
    by_segment?: Record<string, number>;
  };
}

/**
 * customer_service.get_all_kpis() — all 9 customer-domain KPIs. Used
 * here only to surface DAU/WAU/MAU, which /customer/summary omits.
 */
export interface AllCustomerKpis {
  domain: string;
  count: number;
  kpis: Record<string, ActivityKpi>;
}

/** GET /api/v1/customer/kpis */
export function getAllCustomerKpis() {
  return apiGet<AllCustomerKpis>("/api/v1/customer/kpis");
}

export interface RetentionKpi extends KpiResultBase {
  metadata: {
    cohort_size?: number;
    retained_count?: number;
    cohort_month?: string;
    period_months?: number;
  };
}

/** GET /api/v1/customer/retention?period_months=1 */
export function getRetention(periodMonths: number = 1) {
  return apiGet<RetentionKpi>("/api/v1/customer/retention", {
    params: { period_months: periodMonths },
  });
}

export interface ChurnKpi extends KpiResultBase {
  metadata: {
    churned_count?: number;
    prior_active_base?: number;
  };
}

/** GET /api/v1/customer/churn */
export function getChurn() {
  return apiGet<ChurnKpi>("/api/v1/customer/churn");
}

/**
 * customer_service.get_value() — ARPU/CLV/LTV-CAC are registered under
 * the registry's "revenue" domain (implemented in revenue_kpis.py) but
 * are genuine per-customer economics, exposed here via direct registry
 * calls, per the backend's own note (surfaced below, not paraphrased).
 */
export interface CustomerValue {
  arpu: KpiResultBase & { metadata: { total_revenue_gbp?: number; mau?: number } };
  clv: KpiResultBase & {
    metadata: {
      arpu_gbp?: number;
      avg_lifespan_months?: number;
      gross_margin_assumption?: number;
    };
  };
  ltv_cac_ratio: KpiResultBase & {
    metadata: {
      clv_gbp?: number;
      blended_cac_gbp?: number;
      converted_customers?: number;
      benchmark?: string;
    };
  };
  as_of_date: string;
  note: string;
}

/** GET /api/v1/customer/value */
export function getCustomerValue() {
  return apiGet<CustomerValue>("/api/v1/customer/value");
}

/**
 * customer_service.get_segments() — the backend is explicit this is NOT
 * a customer-count-by-segment breakdown (no such KPI exists in the
 * Sprint 5 engine). It exposes revenue_by_segment (net revenue grouped
 * by customer_segment) instead, with gap_note explaining the gap.
 */
export interface CustomerSegments extends KpiResultBase {
  breakdown: {
    by_segment?: Record<string, number>;
  };
  gap_note: string;
}

/** GET /api/v1/customer/segments */
export function getCustomerSegments() {
  return apiGet<CustomerSegments>("/api/v1/customer/segments");
}
