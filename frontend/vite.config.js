import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Proxies /api and /ws to the FastAPI backend (uvicorn on :8000) during
// development so the dashboard can call relative paths with no CORS setup.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
      "/ws": {
        target: "ws://localhost:8000",
        ws: true,
      },
    },
  },
});
