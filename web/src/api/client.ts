import createClient from 'openapi-fetch'
import type { paths } from './schema'

/** Base URL of the API. In dev the Vite proxy maps `/api` to the backend. */
export const API_BASE: string = import.meta.env.VITE_API_BASE ?? `${window.location.origin}/api`

export const api = createClient<paths>({
  baseUrl: API_BASE,
  // Look `fetch` up on each call so tests can replace it.
  fetch: (request) => globalThis.fetch(request),
})
