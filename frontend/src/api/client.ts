// =============================================================================
// frontend/src/api/client.ts
//
// openapi-fetch API client instance.
//
// This module creates a typed HTTP client based on the OpenAPI schema.
// The `paths` type parameter comes from the auto-generated `generated.ts`
// file which is produced by running: npm run generate-api
//
// Usage:
//   import { apiClient } from '@/api/client'
//
//   // GET /api/employees/
//   const { data, error } = await apiClient.GET('/api/employees/', {})
//
//   // POST /api/timesheets/
//   const { data, error } = await apiClient.POST('/api/timesheets/', {
//     body: { employee_id: 1, entry_date: '2026-03-04', minutes: 480 }
//   })
//
// Authentication: the session is an HttpOnly cookie set by POST /api/auth/login.
// JavaScript never sees the token. Every request is sent with credentials, and
// state-changing requests echo the readable CSRF cookie in the X-CSRF-Token header.
// A 401 response (session expired) is announced through `onUnauthorized`.
//
// The base URL is read from the VITE_API_URL environment variable (.env).
// If VITE_API_URL is not set, the fallback relies on Vite's dev proxy.
// =============================================================================

import createClient from "openapi-fetch";
import type { Middleware } from "openapi-fetch";
import type { paths } from "./generated";

export const apiBaseUrl =
  import.meta.env["VITE_API_URL"] ?? import.meta.env.BASE_URL.replace(/\/$/, "");

const CSRF_COOKIE = "ts_csrf";
const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

/** Read the (non-HttpOnly) CSRF cookie set at login, or null if absent. */
export function readCsrfToken(): string | null {
  const entry = document.cookie.split("; ").find((c) => c.startsWith(`${CSRF_COOKIE}=`));
  return entry === undefined ? null : decodeURIComponent(entry.slice(CSRF_COOKIE.length + 1));
}

type UnauthorizedListener = () => void;
let unauthorizedListener: UnauthorizedListener | null = null;

/** Register the callback that runs when the API answers 401 to a non-auth request. */
export function onUnauthorized(listener: UnauthorizedListener | null): void {
  unauthorizedListener = listener;
}

const authMiddleware: Middleware = {
  onRequest({ request }) {
    if (!SAFE_METHODS.has(request.method.toUpperCase())) {
      const csrf = readCsrfToken();
      if (csrf !== null) request.headers.set("X-CSRF-Token", csrf);
    }
    return request;
  },
  onResponse({ request, response }) {
    // A wrong password on /api/auth/login is also 401 and must not log anyone out.
    if (response.status === 401 && !new URL(request.url).pathname.endsWith("/api/auth/login")) {
      unauthorizedListener?.();
    }
    return response;
  },
};

/**
 * Typed API client generated from the FastAPI OpenAPI schema.
 *
 * All request/response types are inferred automatically from the
 * generated `paths` type. TypeScript will error if you use wrong
 * field names, missing required fields, or incorrect types.
 *
 * Regenerate after backend changes: npm run generate-api
 */
export const apiClient = createClient<paths>({
  // Production is hosted below /timesheet; development keeps using Vite's /api proxy.
  baseUrl: apiBaseUrl,
  credentials: "include",
});
apiClient.use(authMiddleware);
