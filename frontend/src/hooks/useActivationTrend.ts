import { getActivationTrend } from "../api/hubs/growth";
import { useApiResource } from "./useApiResource";

/** GET /api/v1/growth/activation-trend?months=6, fetched once on mount. */
export function useActivationTrend() {
  return useApiResource(() => getActivationTrend(6));
}
