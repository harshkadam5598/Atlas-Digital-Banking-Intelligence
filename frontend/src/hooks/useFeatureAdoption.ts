import { getFeatureAdoption } from "../api/hubs/product";
import { useApiResource } from "./useApiResource";

/** GET /api/v1/product/feature-adoption?feature_event_type=..., fetched once on mount. */
export function useFeatureAdoption(featureEventType: string) {
  return useApiResource(() => getFeatureAdoption(featureEventType));
}
