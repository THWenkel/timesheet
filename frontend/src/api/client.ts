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
// The base URL is read from the VITE_API_URL environment variable (.env).
// In development, requests go directly to that URL (CORS is enabled on the backend).
// If VITE_API_URL is not set, the empty string fallback relies on Vite's dev proxy.
// =============================================================================

import createClient from "openapi-fetch";
import type { paths } from "./generated";

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
  // Base URL from .env VITE_API_URL — falls back to '' (Vite proxy) if not set
  baseUrl: import.meta.env.VITE_API_URL ?? "",
});
