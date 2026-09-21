import { getMarketSummary } from "../api/hubs/market";
import { useApiResource } from "./useApiResource";

/** GET /api/v1/market/summary, fetched once on mount. */
export function useMarketSummary() {
  return useApiResource(() => getMarketSummary());
}
