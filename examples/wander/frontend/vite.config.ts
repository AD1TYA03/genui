import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  resolve: {
    dedupe: ["react", "react-dom", "zod", "zustand"],
  },
  plugins: [react(), tailwindcss()],
  build: { chunkSizeWarningLimit: 900 },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
