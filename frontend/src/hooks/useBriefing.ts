import { getBriefing } from "../api/hubs/narrative";
import { useApiResource } from "./useApiResource";

/** GET /api/v1/narrative/briefing, fetched once on mount. */
export function useBriefing() {
  return useApiResource(() => getBriefing());
}
