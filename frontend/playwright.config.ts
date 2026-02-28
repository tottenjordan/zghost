import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 45 * 60 * 1000, // 45 min — 10s pipeline ~25 min + buffer
  expect: {
    timeout: 30_000,
  },
  fullyParallel: false,
  workers: 2, // allow parallel tests (each creates its own session)
  retries: 0, // too long to retry
  reporter: [['html'], ['list']],
  use: {
    baseURL: 'http://localhost:5173',
    actionTimeout: 90_000,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'echo "Start services via ./run_local.sh before running tests"',
    url: 'http://localhost:5173',
    reuseExistingServer: true,
    timeout: 5_000,
  },
});
