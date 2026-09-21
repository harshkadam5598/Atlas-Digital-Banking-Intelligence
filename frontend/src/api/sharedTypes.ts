/**
 * Shared response envelope types — mirror backend/app/schemas/envelope.py
 * exactly. Every /api/v1/* endpoint returns this shape; nothing here is
 * invented on the frontend side.
 */

export interface ResponseMeta {
  as_of_date: string | null;
  generated_at: string;
  cached: boolean;
  cache_ttl_seconds: number | null;
}

export interface ErrorDetail {
  code: string;
  message: string;
}

export interface Envelope<T> {
  data: T | null;
  meta: ResponseMeta | null;
  errors: ErrorDetail[] | null;
}

/**
 * Mirrors analytics/core/types.py Anomaly.to_dict() exactly. Used by
 * Executive (Risk & Alerts), Operations (KYC/Fraud/Transactions), and
 * Market (country-level anomalies) — all three trace to the same
 * anomaly_engine.py output, so this is defined once here rather than
 * as three near-identical hub-local interfaces.
 */
export interface Anomaly {
  metric: string;
  detected_at: string;
  severity: "low" | "medium" | "high" | "critical";
  observed_value: number;
  expected_value: number;
  deviation_pct: number;
  detection_reason: string;
  business_impact: string;
  suggested_investigation: string;
  dimension: string | null;
  metadata: Record<string, unknown>;
}
