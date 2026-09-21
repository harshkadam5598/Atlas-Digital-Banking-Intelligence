import { getRevenueTrend } from "../api/hubs/revenue";
import { useApiResource } from "./useApiResource";

/** GET /api/v1/revenue/trend?granularity=month, fetched once on mount. */
export function useRevenueTrend() {
  return useApiResource(() => getRevenueTrend("month"));
}
