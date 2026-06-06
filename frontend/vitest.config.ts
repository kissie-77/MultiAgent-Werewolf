import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  // react() returns a top-level vite Plugin; vitest bundles its own nested vite
  // whose Plugin type is structurally distinct, so cast to satisfy tsc --noEmit.
  plugins: [react() as never],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
