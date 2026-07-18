import { configDefaults, defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
      "@/features": path.resolve(__dirname, "src/features"),
      "@/components": path.resolve(__dirname, "src/components"),
      "@/services": path.resolve(__dirname, "src/services"),
      "@/hooks": path.resolve(__dirname, "src/hooks"),
      "@/utilities": path.resolve(__dirname, "src/utilities"),
      "@/constants": path.resolve(__dirname, "src/constants"),
      "@/design-system": path.resolve(__dirname, "src/design-system"),
      "@/app": path.resolve(__dirname, "src/app")
    }
  },
  server: {
    port: 5173
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
    css: true,
    exclude: [...configDefaults.exclude, "e2e/**"]
  }
});
