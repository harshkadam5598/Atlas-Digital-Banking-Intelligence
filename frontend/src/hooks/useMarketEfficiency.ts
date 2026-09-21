import { getMarketEfficiency } from "../api/hubs/market";
import { useApiResource } from "./useApiResource";

/** GET /api/v1/market/efficiency, fetched once on mount. */
export function useMarketEfficiency() {
  return useApiResource(() => getMarketEfficiency());
}
