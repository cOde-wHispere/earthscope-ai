import { defineConfig } from "@playwright/test";
import development from "./playwright.config";

const backendServer = Array.isArray(development.webServer)
  ? development.webServer[0]
  : development.webServer!;

export default defineConfig({
  ...development,
  testDir: "./production-e2e",
  outputDir: "./test-results/production",
  use: { ...development.use, baseURL: "http://127.0.0.1:4173" },
  webServer: [
    backendServer,
    {
      command: "npm run preview",
      url: "http://127.0.0.1:4173",
      timeout: 30000,
      reuseExistingServer: !process.env.CI,
    },
  ],
});
