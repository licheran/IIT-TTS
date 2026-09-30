import { defineConfig } from '@playwright/test'
import base from './playwright.config'

// The wiki pictures: `pnpm wiki:shots`. The normal config leaves this spec out.
export default defineConfig({ ...base, testIgnore: [], testMatch: '**/wiki-shots.spec.ts' })
