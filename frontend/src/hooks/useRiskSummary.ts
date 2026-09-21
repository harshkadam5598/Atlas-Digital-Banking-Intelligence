import { getRiskSummary } from "../api/hubs/narrative";
import { useApiResource } from "./useApiResource";

/** GET /api/v1/narrative/risk-summary, fetched once on mount. */
export function useRiskSummary() {
  return useApiResource(() => getRiskSummary());
}
