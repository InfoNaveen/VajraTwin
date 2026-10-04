import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// VajraTwin GCS — Vite config.
// The frontend talks to the FastAPI backend via VITE_API_BASE_URL
// (see services/api.ts); no build-time proxy is required.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
  },
  build: {
    outDir: "dist",
    sourcemap: true,
  },
});
