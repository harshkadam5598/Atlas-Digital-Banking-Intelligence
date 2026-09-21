import { useEffect, useRef, useState } from "react";
import { ApiError, ApiNetworkError } from "../api/errors";

export interface ApiResourceState<T> {
  data: T | null;
  isLoading: boolean;
  error: ApiError | ApiNetworkError | null;
}

/**
 * Fetches once on mount and tracks loading/error state. Shared by the
 * Executive hub's resource hooks so each one isn't a copy-pasted
 * fetch/useEffect block. Deliberately minimal — no caching, retries, or
 * refetch policy. If hub hooks keep multiplying, that's the point at
 * which introducing a query library (e.g. TanStack Query, as the lost
 * Sprint 7 workspace used) would earn its cost; not yet.
 */
export function useApiResource<T>(fetcher: () => Promise<T | null>): ApiResourceState<T> {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<ApiError | ApiNetworkError | null>(null);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  useEffect(() => {
    let cancelled = false;

    setIsLoading(true);
    setError(null);

    fetcherRef
      .current()
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(
            err instanceof ApiError || err instanceof ApiNetworkError
              ? err
              : new ApiNetworkError(err),
          );
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { data, isLoading, error };
}
