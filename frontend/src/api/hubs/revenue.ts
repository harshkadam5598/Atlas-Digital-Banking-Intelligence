import { apiGet } from "../client";

/**
 * Mirrors KPIResult.to_dict() plus the two fields revenue_service adds.
 * `previous_value`/`delta`/`delta_pct`/`trend` are genuinely nullable —
 * KPIResult only populates them when a previous period exists.
 */
export interface RevenueSummary {
  name: string;
  value: number;
  unit: string;
  as_of: string;
  period_label: string;
  previous_value: number | null;
  delta: number | null;
  delta_pct: number | null;
  trend: "up" | "down" | "flat" | null;
  breakdown: Record<string, Record<string, number>>;
  metadata: Record<string, unknown>;
  requested_range: { start_date: string | null; end_date: string | null };
  range_note: string;
}

/** GET /api/v1/revenue/summary */
export function getRevenueSummary() {
  return apiGet<RevenueSummary>("/api/v1/revenue/summary");
}

export interface RevenueTrendPoint {
  period: string;
  actual: number;
}

/**
 * Mirrors revenue_service.get_revenue_trend(). Only granularity="month"
 * has a backing series — any other value returns an empty series plus
 * unavailable_fields, per the backend's own documented limitation.
 */
export interface RevenueTrend {
  granularity: string;
  series: RevenueTrendPoint[];
  unavailable_fields?: Record<string, string>;
}

/** GET /api/v1/revenue/trend */
export function getRevenueTrend(granularity: string = "month") {
  return apiGet<RevenueTrend>("/api/v1/revenue/trend", {
    params: { granularity },
  });
}

export interface RevenueForecastPoint {
  period: string;
  predicted_value: number;
  lower_bound: number;
  upper_bound: number;
}

/** Mirrors ForecastResult.to_dict() plus the horizon_note revenue_service adds. */
export interface RevenueForecast {
  metric: string;
  method: string;
  historical: RevenueTrendPoint[];
  forecast: RevenueForecastPoint[];
  accuracy_note: string;
  metadata: Record<string, unknown>;
  horizon_note: string;
}

/** GET /api/v1/revenue/forecast */
export function getRevenueForecast() {
  return apiGet<RevenueForecast>("/api/v1/revenue/forecast");
}
