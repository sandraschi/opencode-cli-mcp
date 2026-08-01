import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60000,
  retries: 1,
  use: {
    baseURL: "http://127.0.0.1:10950",
    headless: true,
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: "uv run python -m api.main",
      port: 10951,
      cwd: "../",
      env: { PYTHONPATH: "src" },
      timeout: 60000,
      reuseExistingServer: false,
    },
    {
      command: "npx vite --port 10950 --strictPort",
      port: 10950,
      cwd: ".",
      timeout: 60000,
      reuseExistingServer: false,
    },
  ],
});
