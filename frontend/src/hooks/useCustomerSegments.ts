import { getCustomerSegments } from "../api/hubs/customer";
import { useApiResource } from "./useApiResource";

/** GET /api/v1/customer/segments, fetched once on mount. */
export function useCustomerSegments() {
  return useApiResource(() => getCustomerSegments());
}
