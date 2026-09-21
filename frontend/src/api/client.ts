import { ApiError, ApiNetworkError } from "./errors";
import type { Envelope } from "./sharedTypes";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const API_KEY = import.meta.env.VITE_API_KEY ?? "";

export interface RequestOptions {
  /** Query params — undefined values are omitted, not sent as "undefined". */
  params?: Record<string, string | number | undefined>;
}

function buildUrl(path: string, params?: RequestOptions["params"]): string {
  const url = new URL(`${BASE_URL}${path}`);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) {
        url.searchParams.set(key, String(value));
      }
    }
  }
  return url.toString();
}

/**
 * Calls an Atlas API endpoint and returns `data` from the standard
 * envelope. A genuine `null` in `data` is returned as `null` — it is
 * never coerced into a default, zero, or empty-object value here, so
 * callers (hooks, components) can distinguish "backend says none" from
 * "still loading."
 */
export async function apiGet<T>(
  path: string,
  options?: RequestOptions,
): Promise<T | null> {
  const url = buildUrl(path, options?.params);

  let response: Response;
  try {
    response = await fetch(url, {
      method: "GET",
      headers: {
        "X-API-Key": API_KEY,
        Accept: "application/json",
      },
    });
  } catch (cause) {
    throw new ApiNetworkError(cause);
  }

  let envelope: Envelope<T>;
  try {
    envelope = await response.json();
  } catch (cause) {
    throw new ApiNetworkError(cause);
  }

  if (!response.ok || envelope.errors) {
    throw new ApiError(response.status, envelope.errors ?? []);
  }

  return envelope.data;
}
