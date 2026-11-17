import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  webServer: {
    command: ".venv/bin/python -m scripts.e2e_server",
    url: "http://127.0.0.1:5175",
    reuseExistingServer: false,
    timeout: 60000,
  },
  use: {
    browserName:
      process.env.PLAYWRIGHT_BROWSER === "webkit" ? "webkit" : "chromium",
    baseURL: "http://127.0.0.1:5175",
    headless: true,
    viewport: { width: 1440, height: 960 },
    launchOptions: {
      executablePath:
        process.env.PLAYWRIGHT_BROWSER === "webkit"
          ? undefined
          : process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE,
    },
  },
  workers: 1,
});
