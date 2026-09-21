import { getProductSummary } from "../api/hubs/product";
import { useApiResource } from "./useApiResource";

/** GET /api/v1/product/summary, fetched once on mount. */
export function useProductSummary() {
  return useApiResource(() => getProductSummary());
}
