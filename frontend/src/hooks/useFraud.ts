import { getFraud } from "../api/hubs/operations";
import { useApiResource } from "./useApiResource";

/** GET /api/v1/operations/fraud, fetched once on mount. */
export function useFraud() {
  return useApiResource(() => getFraud());
}
