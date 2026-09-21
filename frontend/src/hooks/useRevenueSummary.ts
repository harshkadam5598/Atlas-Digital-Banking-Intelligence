import { getRevenueSummary } from "../api/hubs/revenue";
import { useApiResource } from "./useApiResource";

/** GET /api/v1/revenue/summary, fetched once on mount. */
export function useRevenueSummary() {
  return useApiResource(() => getRevenueSummary());
}
