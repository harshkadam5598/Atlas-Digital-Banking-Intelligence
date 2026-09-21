import { getFunnel } from "../api/hubs/growth";
import { useApiResource } from "./useApiResource";

/** GET /api/v1/growth/funnel, fetched once on mount. */
export function useFunnel() {
  return useApiResource(() => getFunnel());
}
