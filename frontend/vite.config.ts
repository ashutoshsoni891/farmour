/// <reference types="vitest/config" />
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: "prompt",
      // App shell only in M0; the offline data queue arrives with records (M6).
      workbox: {
        globPatterns: ["**/*.{js,css,html,svg,woff2}"],
        navigateFallback: "/index.html",
        navigateFallbackDenylist: [/^\/api\//, /^\/auth\//], // /login/callback stays in the SPA
      },
      manifest: {
        name: "Farm",
        short_name: "Farm",
        lang: "hi",
        display: "standalone",
        start_url: "/",
        background_color: "#ffffff",
        theme_color: "#1f5f2e",
        icons: [{ src: "/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" }],
      },
    }),
  ],
  server: {
    proxy: { "/api": "http://localhost", "/auth": "http://localhost" },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
