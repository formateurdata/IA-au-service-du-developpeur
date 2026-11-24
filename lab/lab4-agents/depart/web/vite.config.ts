import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // L'interface appelle /api/... ; Vite transmet à l'API sur le port 8000.
    proxy: { "/api": "http://localhost:8000" },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/setupTests.ts"],
  },
});
