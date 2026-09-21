import { getHealthScore } from "../api/hubs/executive";
import { useApiResource } from "./useApiResource";

/** GET /api/v1/executive/health-score, fetched once on mount. */
export function useHealthScore() {
  return useApiResource(() => getHealthScore());
}
