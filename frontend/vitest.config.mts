import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";

// Birim testleri: tarayıcı gerektirmeyen saf mantık (src/lib/**).
// `@/` takma adı tsconfig.json'daki paths ile aynı.
export default defineConfig({
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  test: {
    include: ["src/**/*.test.ts"],
  },
});
