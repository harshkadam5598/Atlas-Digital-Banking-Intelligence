import { getChurn } from "../api/hubs/customer";
import { useApiResource } from "./useApiResource";

/** GET /api/v1/customer/churn, fetched once on mount. */
export function useChurn() {
  return useApiResource(() => getChurn());
}
