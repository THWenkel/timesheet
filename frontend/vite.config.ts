// =============================================================================
// frontend/vite.config.ts
//
// Vite build and dev server configuration.
//
// Key configuration:
//   - React plugin with fast HMR
//   - Path alias @/ → src/ for clean imports
//   - Base path from VITE_BASE_PATH (default /timesheet/), see .env.proxypath / .env.domain
//   - Dev server proxy: /api → http://localhost:8000
//     This means the frontend never makes cross-origin requests in development —
//     no CORS configuration needed on the backend for local development.
// =============================================================================

import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd());
  const apiUrl = env.VITE_API_URL || "http://localhost:8000";

  return {
    plugins: [react()],
    // Public base path. "/timesheet/" under IIS path routing (default, build:path); "/" for the own
    // domain behind the reverse proxy (npm run build:domain, see .env.proxypath / .env.domain).
    base: env.VITE_BASE_PATH || "/timesheet/",

    resolve: {
      alias: {
        // @/ maps to src/ — allows imports like: import { client } from '@/api/client'
        "@": resolve(__dirname, "src"),
      },
    },

    server: {
      port: 5173,

      proxy: {
        // All requests to /api/* are proxied to the FastAPI backend.
        // Target is read from VITE_API_URL in .env (fallback: http://localhost:8000).
        // This eliminates CORS issues during development — the browser sees all
        // traffic as coming from localhost:5173.
        "/api": {
          target: apiUrl,
          changeOrigin: true,
          // No rewrite needed — backend routes are also prefixed with /api
        },
      },
    },

    build: {
      // Target modern browsers — adjust if older browser support is needed
      target: "es2022",
      outDir: "dist",
      sourcemap: true,
    },
  };
});
