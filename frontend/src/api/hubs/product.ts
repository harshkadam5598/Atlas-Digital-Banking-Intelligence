import { apiGet } from "../client";

/** product_service.get_summary() — 3 raw headline values, no delta/trend. */
export interface ProductSummary {
  product_adoption: number;
  product_stickiness: number;
  cross_sell_rate: number;
  as_of_date: string;
}

/** GET /api/v1/product/summary */
export function getProductSummary() {
  return apiGet<ProductSummary>("/api/v1/product/summary");
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
 * Mirrors product_kpis.product_adoption(). value = overall adoption rate
 * (whole percent); breakdown.by_product = per-product adoption rate,
 * each already a whole-percent number too.
 */
export interface ProductAdoption extends KpiResultBase {
  breakdown: {
    by_product?: Record<string, number>;
  };
  metadata: {
    active_customer_base?: number;
  };
}

/** GET /api/v1/product/adoption */
export function getProductAdoption() {
  return apiGet<ProductAdoption>("/api/v1/product/adoption");
}

/**
 * Mirrors product_kpis.product_stickiness(). unit="ratio" (DAU/MAU,
 * e.g. 0.24, NOT a percent) for both the headline value and every
 * per-product breakdown entry. metadata.benchmark is the backend's own
 * real threshold text, not something to invent client-side.
 */
export interface ProductStickiness extends KpiResultBase {
  breakdown: {
    by_product?: Record<string, number>;
  };
  metadata: {
    benchmark?: string;
  };
}

/** GET /api/v1/product/stickiness */
export function getProductStickiness() {
  return apiGet<ProductStickiness>("/api/v1/product/stickiness");
}

/**
 * Mirrors product_kpis.cross_sell_rate(). breakdown.product_count_distribution
 * maps a stringified product count ("1", "2", "3", ...) to the number of
 * active customers holding that many distinct products.
 */
export interface CrossSellRate extends KpiResultBase {
  breakdown: {
    product_count_distribution?: Record<string, number>;
  };
  metadata: {
    active_base?: number;
    multi_product_count?: number;
  };
}

/** GET /api/v1/product/cross-sell */
export function getCrossSellRate() {
  return apiGet<CrossSellRate>("/api/v1/product/cross-sell");
}

/**
 * Mirrors product_kpis.feature_adoption(). feature_event_type must be a
 * real fact_product_events.event_type value — see
 * etl/extractors/product_event_generator.py's event_map for the actual
 * set generated (premium_purchased, crypto_activated, investment_opened,
 * fx_activated, card_activated, savings_opened, transfer_activated).
 */
export interface FeatureAdoption extends KpiResultBase {
  metadata: {
    feature_event_type?: string;
    feature_users?: number;
    eligible_base?: number;
  };
}

/** GET /api/v1/product/feature-adoption?feature_event_type=... */
export function getFeatureAdoption(featureEventType: string) {
  return apiGet<FeatureAdoption>("/api/v1/product/feature-adoption", {
    params: { feature_event_type: featureEventType },
  });
}
