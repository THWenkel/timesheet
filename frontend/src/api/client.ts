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
// The base URL is empty ('') because all /api/* requests are proxied to the
// backend by Vite's dev server proxy. In production, the same proxy logic
// should be handled by a reverse proxy (nginx, etc.).
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
  // Base URL is empty — /api/* requests are handled by Vite's proxy
  baseUrl: "",
});
