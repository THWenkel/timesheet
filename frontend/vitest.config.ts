// =============================================================================
// frontend/vitest.config.ts
//
// Vitest test runner configuration.
//
// Uses jsdom environment to simulate a browser DOM for React component tests.
// Globals are enabled so tests can use describe/it/expect without imports.
// =============================================================================

import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

export default defineConfig({
  plugins: [react()],

  resolve: {
    alias: {
      "@": resolve(__dirname, "src"),
    },
  },

  test: {
    // Use jsdom to simulate browser DOM for React component testing
    environment: "jsdom",

    // Enable Vitest globals (describe, it, expect, etc.) without explicit imports
    globals: true,

    // Setup file runs before each test file — sets up Testing Library matchers
    setupFiles: ["./src/test/setup.ts"],

    // Coverage configuration (run with: npm run test:coverage)
    coverage: {
      provider: "v8",
      reporter: ["text", "html", "lcov"],
      exclude: [
        "src/api/generated.ts", // Auto-generated file
        "src/test/**",
        "**/*.d.ts",
        "vite.config.ts",
        "vitest.config.ts",
      ],
    },

    // Include test files matching these patterns
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
  },
});
