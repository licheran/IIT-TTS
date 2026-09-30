import { defineConfig } from '@playwright/test'

// Every run gets a database of its own. This file is loaded more than once (by the runner and by
// each worker process), so the name is chosen once and passed on through the environment.
process.env.E2E_DB ??= `e2e-${Date.now()}.db`
const DB_URL = `sqlite:///${process.env.E2E_DB}`

const API_PORT = 8100
const WEB_PORT = 5180

export default defineConfig({
  testDir: './e2e',
  testIgnore: '**/wiki-shots.spec.ts',
  timeout: 180_000,
  fullyParallel: false,
  workers: 1,
  globalSetup: './e2e/global-setup.ts',
  use: { baseURL: `http://localhost:${WEB_PORT}`, acceptDownloads: true },
  // The worker is started by the global setup. The API and Vite are started here, on a
  // temporary database and on ports of their own, so `docker compose up` can keep running.
  webServer: [
    {
      command: `uv run uvicorn tts.api.main:app --port ${API_PORT}`,
      cwd: '../backend',
      url: `http://localhost:${API_PORT}/health`,
      env: { TT_DATABASE_URL: DB_URL },
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: `pnpm exec vite --port ${WEB_PORT} --strictPort`,
      url: `http://localhost:${WEB_PORT}`,
      env: { VITE_API_URL: `http://localhost:${API_PORT}` },
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
})
