import { getGeographic } from "../api/hubs/market";
import { useApiResource } from "./useApiResource";

/** GET /api/v1/market/geographic, fetched once on mount. */
export function useGeographic() {
  return useApiResource(() => getGeographic());
}
