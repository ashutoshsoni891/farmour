import createClient from "openapi-fetch";

import type { paths } from "./schema";

export interface ApiError {
  code: string;
  message_key: string;
  details: Record<string, unknown>;
}

export function apiClient(token: string | null) {
  return createClient<paths>({
    baseUrl: "/",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
}

/** i18n key for an error body from the API (spec section 12), or a network error. */
export function errorKey(error: unknown): string {
  if (error && typeof error === "object" && "error" in error) {
    const e = (error as { error: Partial<ApiError> }).error;
    if (typeof e.message_key === "string") return e.message_key;
  }
  return "err.internal_error";
}
