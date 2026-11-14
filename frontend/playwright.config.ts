import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "desktop",
      use: {
        ...devices["Desktop Chrome"],
        channel: "chrome",
        viewport: { width: 1440, height: 1000 },
      },
    },
    { name: "mobile", use: { ...devices["Pixel 7"], channel: "chrome" } },
  ],
  webServer: [
    {
      command:
        process.platform === "win32"
          ? "..\\backend\\.venv\\Scripts\\python.exe -m uvicorn earthscope_backend.main:app --host 127.0.0.1 --port 8000"
          : "../backend/.venv/bin/python -m uvicorn earthscope_backend.main:app --host 127.0.0.1 --port 8000",
      url: "http://127.0.0.1:8000/health",
      timeout: 30000,
      reuseExistingServer: !process.env.CI,
    },
    {
      command: "npm run dev",
      url: "http://127.0.0.1:5173",
      timeout: 30000,
      reuseExistingServer: !process.env.CI,
    },
  ],
});
