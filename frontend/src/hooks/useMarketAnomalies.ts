import { getMarketAnomalies } from "../api/hubs/market";
import { useApiResource } from "./useApiResource";

/** GET /api/v1/market/anomalies, fetched once on mount. */
export function useMarketAnomalies() {
  return useApiResource(() => getMarketAnomalies());
}
