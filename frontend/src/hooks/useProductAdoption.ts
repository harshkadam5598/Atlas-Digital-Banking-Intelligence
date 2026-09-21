import { getProductAdoption } from "../api/hubs/product";
import { useApiResource } from "./useApiResource";

/** GET /api/v1/product/adoption, fetched once on mount. */
export function useProductAdoption() {
  return useApiResource(() => getProductAdoption());
}
