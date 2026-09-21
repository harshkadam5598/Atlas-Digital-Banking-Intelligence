import { getKyc } from "../api/hubs/operations";
import { useApiResource } from "./useApiResource";

/** GET /api/v1/operations/kyc, fetched once on mount. */
export function useKyc() {
  return useApiResource(() => getKyc());
}
