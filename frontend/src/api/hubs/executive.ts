/**
 * Types mirror backend/app/services/executive_service.py exactly.
 * `activation_rate` and `risk_score` are always null in the current
 * backend (no backing KPI implementation yet — see `unavailable_fields`)
 * and are typed as such rather than hidden.
 */
import { apiGet } from "../client";

export interface ExecutiveKpis {
  mau: number;
  mau_growth_mom: number | null;
  revenue_mtd: number;
  revenue_growth_mom: number;
  activation_rate: null;
  premium_conversion_rate: number;
  churn_rate_monthly: number;
  risk_score: null;
  as_of_date: string;
  unavailable_fields: Record<string, string>;
}

/** GET /api/v1/executive/kpis — the only endpoint this milestone consumes. */
export function getExecutiveKpis(asOf?: string) {
  return apiGet<ExecutiveKpis>("/api/v1/executive/kpis", {
    params: { as_of: asOf },
  });
}

/**
 * Mirrors executive_service.get_health_score_components() exactly.
 * `score`/`rating` are always null (no composite scoring implemented
 * yet — see `unavailable_fields`); of the five weighted components,
 * only `retention_30d` and `revenue_growth_mom` have real values.
 */
export interface HealthScoreComponents {
  score: null;
  rating: null;
  components: {
    retention_30d: number;
    revenue_growth_mom: number;
    activation_rate: null;
    nps_proxy: null;
    operational_uptime: null;
  };
  as_of_date: string;
  formula: string;
  unavailable_fields: Record<string, string>;
}

/** GET /api/v1/executive/health-score */
export function getHealthScore(asOf?: string) {
  return apiGet<HealthScoreComponents>("/api/v1/executive/health-score", {
    params: { as_of: asOf },
  });
}
