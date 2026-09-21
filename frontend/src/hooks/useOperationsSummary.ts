import { getOperationsSummary } from "../api/hubs/operations";
import { useApiResource } from "./useApiResource";

/** GET /api/v1/operations/summary, fetched once on mount. */
export function useOperationsSummary() {
  return useApiResource(() => getOperationsSummary());
}
