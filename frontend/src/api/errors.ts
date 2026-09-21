import type { ErrorDetail } from "./sharedTypes";

/**
 * Thrown when the API responded (any status) but the envelope carried
 * one or more errors — e.g. 401 UNAUTHORIZED, 404 NOT_FOUND,
 * 503 DATA_UNAVAILABLE. See backend/app/core/exceptions.py for the
 * full set of stable `code` values.
 */
export class ApiError extends Error {
  readonly status: number;
  readonly errors: ErrorDetail[];

  constructor(status: number, errors: ErrorDetail[]) {
    super(errors[0]?.message ?? `Request failed with status ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.errors = errors;
  }
}

/**
 * Thrown when the request never reached the server (DNS/connection
 * failure, CORS rejection, etc.) — distinct from ApiError so callers
 * can tell "the API said no" from "the API was unreachable."
 */
export class ApiNetworkError extends Error {
  constructor(cause: unknown) {
    super("Unable to reach the Atlas API.");
    this.name = "ApiNetworkError";
    this.cause = cause;
  }
}
