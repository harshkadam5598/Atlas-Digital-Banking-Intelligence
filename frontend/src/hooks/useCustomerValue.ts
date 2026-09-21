import { getCustomerValue } from "../api/hubs/customer";
import { useApiResource } from "./useApiResource";

/** GET /api/v1/customer/value, fetched once on mount. */
export function useCustomerValue() {
  return useApiResource(() => getCustomerValue());
}
