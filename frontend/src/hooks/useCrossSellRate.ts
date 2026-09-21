import { getCrossSellRate } from "../api/hubs/product";
import { useApiResource } from "./useApiResource";

/** GET /api/v1/product/cross-sell, fetched once on mount. */
export function useCrossSellRate() {
  return useApiResource(() => getCrossSellRate());
}
