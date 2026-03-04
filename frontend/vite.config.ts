// =============================================================================
// frontend/vite.config.ts
//
// Vite build and dev server configuration.
//
// Key configuration:
//   - React plugin with fast HMR
//   - Path alias @/ → src/ for clean imports
//   - Dev server proxy: /api → http://localhost:8000
//     This means the frontend never makes cross-origin requests in development —
//     no CORS configuration needed on the backend for local development.
// =============================================================================

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

export default defineConfig({
  plugins: [react()],

  resolve: {
    alias: {
      // @/ maps to src/ — allows imports like: import { client } from '@/api/client'
      "@": resolve(__dirname, "src"),
    },
  },

  server: {
    port: 5173,

    proxy: {
      // All requests to /api/* are proxied to the FastAPI backend on port 8000.
      // This eliminates CORS issues during development — the browser sees all
      // traffic as coming from localhost:5173.
      "/api": {
        target: "http://localhost:8000",
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
});
