import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  timeout: 120_000,
  use: { baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:5173' },
  // Assumes the API, the worker and Vite are already running (`docker compose up`).
  // Phase 7 replaces this with a webServer that starts them on a temporary database.
})
