import { getAllCustomerKpis } from "../api/hubs/customer";
import { useApiResource } from "./useApiResource";

/** GET /api/v1/customer/kpis, fetched once on mount. */
export function useAllCustomerKpis() {
  return useApiResource(() => getAllCustomerKpis());
}
