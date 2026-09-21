import { getProductStickiness } from "../api/hubs/product";
import { useApiResource } from "./useApiResource";

/** GET /api/v1/product/stickiness, fetched once on mount. */
export function useProductStickiness() {
  return useApiResource(() => getProductStickiness());
}
