import { defineConfig, devices } from "@playwright/test";

// Mobile viewport by default (spec section 13: mid-range Android over 3G).
export default defineConfig({
  testDir: "e2e",
  use: { ...devices["Pixel 7"], baseURL: "http://localhost:4173" },
  webServer: { command: "pnpm build && pnpm preview", port: 4173, reuseExistingServer: true },
});
