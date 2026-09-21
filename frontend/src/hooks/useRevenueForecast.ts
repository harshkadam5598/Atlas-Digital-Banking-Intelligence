import { getRevenueForecast } from "../api/hubs/revenue";
import { useApiResource } from "./useApiResource";

/** GET /api/v1/revenue/forecast, fetched once on mount. */
export function useRevenueForecast() {
  return useApiResource(() => getRevenueForecast());
}
