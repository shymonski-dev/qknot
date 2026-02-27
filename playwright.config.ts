import { defineConfig, devices } from '@playwright/test';

const isCI = !!process.env.CI;
const hasIBMToken = !!process.env.IBM_QUANTUM_TOKEN;

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: isCI,
  retries: isCI ? 1 : 0,
  workers: 1,
  reporter: isCI ? 'list' : 'html',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'on-first-failure',
  },

  projects: [
    {
      name: 'mocked',
      testMatch: 'e2e/mocked/**/*.spec.ts',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'live',
      testMatch: 'e2e/live/**/*.spec.ts',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  webServer: [
    {
      command:
        'IBM_QUANTUM_TOKEN="test" backend/.venv/bin/python -m uvicorn backend.main:app --port 8000',
      url: 'http://localhost:8000/api/health',
      reuseExistingServer: !isCI,
      timeout: 30_000,
    },
    {
      command: 'npm run dev',
      url: 'http://localhost:3000',
      reuseExistingServer: !isCI,
      timeout: 30_000,
    },
  ],
});
