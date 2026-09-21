import { getCacByChannel } from "../api/hubs/growth";
import { useApiResource } from "./useApiResource";

/** GET /api/v1/growth/cac-by-channel, fetched once on mount. */
export function useCacByChannel() {
  return useApiResource(() => getCacByChannel());
}
