import { getSupport } from "../api/hubs/operations";
import { useApiResource } from "./useApiResource";

/** GET /api/v1/operations/support, fetched once on mount. */
export function useSupport() {
  return useApiResource(() => getSupport());
}
