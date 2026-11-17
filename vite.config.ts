import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  root: "apps/web",
  build: {
    outDir: "../../dist",
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks: { charts: ["recharts"], icons: ["lucide-react"] },
      },
    },
  },
  server: {
    strictPort: true,
    proxy: { "/api": process.env.VITE_API_TARGET || "http://127.0.0.1:8000" },
  },
});
