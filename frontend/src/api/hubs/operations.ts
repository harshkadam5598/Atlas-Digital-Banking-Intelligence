import { apiGet } from "../client";
import type { Anomaly } from "../sharedTypes";

/** operations_service.get_summary() — 5 raw headline values, no delta/trend/targets. */
export interface OperationsSummary {
  kyc_approval_rate: number;
  fraud_rate: number;
  support_resolution_time: number;
  csat: number;
  failed_transaction_rate: number;
  as_of_date: string;
}

/** GET /api/v1/operations/summary */
export function getOperationsSummary() {
  return apiGet<OperationsSummary>("/api/v1/operations/summary");
}

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

/**
 * Same shape as every other hub's anomaly type — see api/sharedTypes.ts.
 * All trace to the same anomaly_engine.py Anomaly.to_dict(), so the
 * existing AnomalyCard component is reused directly rather than duplicated.
 */
export type OperationsAnomaly = Anomaly;

export interface KycApprovalRate extends KpiResultBase {
  breakdown: { by_country?: Record<string, number> };
  metadata: { target?: number; total_submissions?: number; approved?: number };
}

export interface KycProcessingTime extends KpiResultBase {
  metadata: { target_hours?: number; mean_hours?: number; sample_size?: number };
}

export interface OperationsKyc {
  kyc_approval_rate: KycApprovalRate;
  kyc_processing_time: KycProcessingTime;
  anomalies: OperationsAnomaly[];
  as_of_date: string;
}

/** GET /api/v1/operations/kyc */
export function getKyc() {
  return apiGet<OperationsKyc>("/api/v1/operations/kyc");
}

export interface FraudRate extends KpiResultBase {
  metadata: {
    flagged_count?: number;
    cleared_count?: number;
    chargeback_count?: number;
    clear_ratio_pct?: number;
    completed_transactions?: number;
  };
}

export interface OperationsFraud {
  fraud_rate: FraudRate;
  anomalies: OperationsAnomaly[];
  as_of_date: string;
}

/** GET /api/v1/operations/fraud */
export function getFraud() {
  return apiGet<OperationsFraud>("/api/v1/operations/fraud");
}

export interface SupportResolutionTime extends KpiResultBase {
  breakdown: { by_priority?: Record<string, number> };
  metadata: { targets?: Record<string, number>; resolved_tickets?: number };
}

export interface Csat extends KpiResultBase {
  breakdown: { by_tier?: { premium: number; free: number } };
  metadata: { scale?: string; rated_tickets?: number };
}

export interface OperationsSupport {
  support_resolution_time: SupportResolutionTime;
  csat: Csat;
  as_of_date: string;
}

/** GET /api/v1/operations/support */
export function getSupport() {
  return apiGet<OperationsSupport>("/api/v1/operations/support");
}

export interface FailedTransactionRate extends KpiResultBase {
  breakdown: { by_product?: Record<string, number> };
  metadata: { alert_threshold?: number; failed_count?: number; total_transactions?: number };
}

export interface OperationsTransactions {
  failed_transaction_rate: FailedTransactionRate;
  anomalies: OperationsAnomaly[];
  as_of_date: string;
}

/** GET /api/v1/operations/transactions */
export function getTransactions() {
  return apiGet<OperationsTransactions>("/api/v1/operations/transactions");
}
