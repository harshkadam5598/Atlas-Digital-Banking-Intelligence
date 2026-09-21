import { getCustomerSummary } from "../api/hubs/customer";
import { useApiResource } from "./useApiResource";

/** GET /api/v1/customer/summary, fetched once on mount. */
export function useCustomerSummary() {
  return useApiResource(() => getCustomerSummary());
}
