import { apiGet } from "../client";

/**
 * All three Growth capabilities return KPIResult.to_dict() shapes
 * (see analytics/core/types.py) unmodified — growth_service.py does not
 * rescale values the way executive_service.py does, so `value`/
 * `delta_pct` here are already whole percent (e.g. 42.5 = 42.5%), not
 * fractions. growth_kpis functions never pass previous_value, so
 * previous_value/delta/delta_pct/trend are always null in practice —
 * typed as nullable rather than assumed absent, in case that changes.
 */
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

export interface FunnelStageCounts {
  registrations: number;
  kyc_started: number;
  kyc_approved: number;
  activated: number;
  first_transaction: number;
  premium_upgrades: number;
}

export interface FunnelStageConversionRates {
  registration_to_kyc_started: number;
  kyc_started_to_approved: number;
  kyc_approved_to_activated: number;
  activated_to_first_transaction: number;
  free_to_premium: number;
}

/**
 * `value` = registrations -> first_transaction conversion, whole percent.
 * `breakdown` is empty ({}) in the backend's no-data/no-registrations
 * early-return paths, so both keys are optional.
 */
export interface FunnelConversion extends KpiResultBase {
  breakdown: {
    stage_counts?: FunnelStageCounts;
    stage_conversion_rates?: FunnelStageConversionRates;
  };
  metadata: {
    note?: string;
    registrations?: number;
  };
}

/** GET /api/v1/growth/funnel */
export function getFunnel() {
  return apiGet<FunnelConversion>("/api/v1/growth/funnel");
}

/**
 * `value` = blended CAC (total spend / total converted) in GBP.
 * Channels with 0 converted customers appear in `by_channel` with a
 * CAC of 0.0 — the backend's own note explains this means "not
 * computable", not "free acquisition".
 */
export interface CacByChannel extends KpiResultBase {
  breakdown: {
    by_channel?: Record<string, number>;
    spend_by_channel?: Record<string, number>;
    converted_by_channel?: Record<string, number>;
  };
  metadata: {
    converted_definition?: string;
    note?: string | null;
  };
}

/** GET /api/v1/growth/cac-by-channel */
export function getCacByChannel() {
  return apiGet<CacByChannel>("/api/v1/growth/cac-by-channel");
}

export interface ActivationTrendPoint {
  period: string;
  /** Whole percent, e.g. 42.5 = 42.5%. */
  activation_rate: number;
  registrations: number;
}

/** Mirrors growth_service.get_activation_trend(). */
export interface ActivationTrend {
  granularity: string;
  series: ActivationTrendPoint[];
}

/** GET /api/v1/growth/activation-trend?months=N (backend allows 1–24, default 6). */
export function getActivationTrend(months: number = 6) {
  return apiGet<ActivationTrend>("/api/v1/growth/activation-trend", {
    params: { months },
  });
}
