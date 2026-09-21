import { getExecutiveKpis } from "../api/hubs/executive";
import { useApiResource } from "./useApiResource";

/** GET /api/v1/executive/kpis, fetched once on mount. */
export function useExecutiveKpis() {
  return useApiResource(() => getExecutiveKpis());
}
