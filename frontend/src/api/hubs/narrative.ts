import { apiGet } from "../client";
import type { Anomaly } from "../sharedTypes";

/** Mirrors analytics/core/types.py Insight.to_dict(). */
export interface NarrativeInsight {
  headline: string;
  category: string;
  direction: "up" | "down" | "flat";
  magnitude_pct: number;
  primary_driver: string;
  contributing_factors: string[];
  supporting_kpis: string[];
  is_opportunity: boolean;
  is_risk: boolean;
  confidence: "low" | "medium" | "high";
  metadata: Record<string, unknown>;
}

/** Mirrors analytics/core/types.py Recommendation.to_dict(). */
export interface NarrativeRecommendation {
  title: string;
  rationale: string;
  supporting_kpis: string[];
  estimated_impact: string;
  priority: "Low" | "Medium" | "High";
  category: string;
  rule_id: string;
  metadata: Record<string, unknown>;
}

/** Mirrors narrative_service.get_briefing(). */
export interface ExecutiveBriefing {
  insight_count: number;
  risk_count: number;
  opportunity_count: number;
  recommendation_count: number;
  top_insights: NarrativeInsight[];
  top_recommendations: NarrativeRecommendation[];
}

/** GET /api/v1/narrative/briefing */
export function getBriefing(maxInsights?: number, maxRecommendations?: number) {
  return apiGet<ExecutiveBriefing>("/api/v1/narrative/briefing", {
    params: {
      max_insights: maxInsights,
      max_recommendations: maxRecommendations,
    },
  });
}

/** Same shape as every other hub's anomaly type — see api/sharedTypes.ts. */
export type NarrativeAnomaly = Anomaly;

/** Mirrors narrative_service.get_risk_summary(). Already severity-sorted by the backend. */
export interface RiskSummary {
  risk_insight_count: number;
  anomaly_count: number;
  risk_recommendation_count: number;
  risk_insights: NarrativeInsight[];
  anomalies: NarrativeAnomaly[];
  risk_recommendations: NarrativeRecommendation[];
}

/** GET /api/v1/narrative/risk-summary */
export function getRiskSummary() {
  return apiGet<RiskSummary>("/api/v1/narrative/risk-summary");
}
