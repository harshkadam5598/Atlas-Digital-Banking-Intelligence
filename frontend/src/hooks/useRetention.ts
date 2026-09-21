import { getRetention } from "../api/hubs/customer";
import { useApiResource } from "./useApiResource";

/** GET /api/v1/customer/retention?period_months=1, fetched once on mount. */
export function useRetention() {
  return useApiResource(() => getRetention(1));
}
