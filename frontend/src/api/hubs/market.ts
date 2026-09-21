import { apiGet } from "../client";
import type { Anomaly } from "../sharedTypes";

/**
 * Mirrors market_service.get_summary(). ltv_cac_ratio is exposed here
 * as the acquisition-efficiency proxy the backend documents — see
 * efficiency_note, rendered verbatim, not paraphrased into a stronger
 * claim than the backend makes.
 */
export interface MarketSummary {
  total_revenue: number;
  top_countries_by_revenue: Record<string, number>;
  ltv_cac_ratio: number;
  as_of_date: string;
  efficiency_note: string;
}

/** GET /api/v1/market/summary */
export function getMarketSummary() {
  return apiGet<MarketSummary>("/api/v1/market/summary");
}

/**
 * Mirrors market_service.get_geographic(). Neither
 * geographic_revenue_contribution_pct nor country_customer_growth_rate_mom
 * is a registered KPI — both are plain arithmetic derived at the API
 * layer from revenue_by_country() and two new_customers() calls, per
 * the backend's own `note`.
 *
 * country_customer_growth_rate_mom[country] carries three genuinely
 * distinct states, all produced by the backend itself:
 *   - a negative number: real decline (including exactly -100 when a
 *     country had customers last month and none this month)
 *   - a positive number: real growth
 *   - null: no prior-month base to compare against (undefined MoM rate)
 * None of these should be collapsed into 0 or hidden.
 */
export interface MarketGeographic {
  revenue_by_country: Record<string, number>;
  total_revenue: number;
  geographic_revenue_contribution_pct: Record<string, number>;
  country_customer_growth_rate_mom: Record<string, number | null>;
  new_customers_current_month: Record<string, number>;
  new_customers_previous_month: Record<string, number>;
  as_of_date: string;
  note: string;
}

/** GET /api/v1/market/geographic */
export function getGeographic() {
  return apiGet<MarketGeographic>("/api/v1/market/geographic");
}

/** Same shape as every other hub's anomaly type — see api/sharedTypes.ts. */
export type MarketAnomaly = Anomaly;

export interface MarketAnomalies {
  count: number;
  anomalies: MarketAnomaly[];
}

/** GET /api/v1/market/anomalies */
export function getMarketAnomalies() {
  return apiGet<MarketAnomalies>("/api/v1/market/anomalies");
}

/**
 * Mirrors market_service.get_efficiency() — ltv_cac_ratio's KPIResult
 * plus proxy_note. The backend is explicit there is no formally defined
 * "Market Efficiency" KPI; this is the closest real proxy, not a claim
 * of an official metric. Same underlying function as Customer's
 * /value endpoint, so the same "0.0 means not computable" caveat
 * applies via metadata.converted_customers.
 */
export interface MarketEfficiency {
  name: string;
  value: number;
  unit: string;
  as_of: string;
  period_label: string;
  previous_value: number | null;
  delta: number | null;
  delta_pct: number | null;
  trend: "up" | "down" | "flat" | null;
  metadata: {
    clv_gbp?: number;
    blended_cac_gbp?: number;
    converted_customers?: number;
    benchmark?: string;
  };
  proxy_note: string;
}

/** GET /api/v1/market/efficiency */
export function getMarketEfficiency() {
  return apiGet<MarketEfficiency>("/api/v1/market/efficiency");
}
