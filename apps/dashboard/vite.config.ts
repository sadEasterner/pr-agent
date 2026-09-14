import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@gitea-pr-manager/ui": path.resolve(__dirname, "../../packages/ui/src/index.tsx"),
      "@gitea-pr-manager/shared-types": path.resolve(
        __dirname,
        "../../packages/shared-types/src/index.ts",
      ),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": process.env.API_PROXY ?? "http://localhost:8000",
      "/health": process.env.API_PROXY ?? "http://localhost:8000",
      "/ready": process.env.API_PROXY ?? "http://localhost:8000",
      "/webhooks": process.env.API_PROXY ?? "http://localhost:8000",
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
  },
});
