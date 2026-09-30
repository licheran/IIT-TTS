import createClient from 'openapi-fetch'
import type { paths } from './schema'

/** Base URL of the API. In dev the Vite proxy maps `/api` to the backend. */
export const API_BASE: string = import.meta.env.VITE_API_BASE ?? `${window.location.origin}/api`

export const api = createClient<paths>({
  baseUrl: API_BASE,
  // Look `fetch` up on each call so tests can replace it.
  fetch: (request) => globalThis.fetch(request),
})

/** One problem inside an error's `details` (a row-level import problem or a request field). */
export interface ErrorDetail {
  sheet?: string
  row?: number | null
  column?: string | null
  message?: string
  text?: string
  where?: string
}

/** The API's standard error shape: `{"error": {"code", "message", "details"}}`. */
export class ApiError extends Error {
  status: number
  code: string
  details: ErrorDetail[]

  constructor(status: number, code: string, message: string, details: ErrorDetail[] = []) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

export function toApiError(status: number, body: unknown): ApiError {
  const error = (body as { error?: { code?: string; message?: string; details?: unknown } } | null)
    ?.error
  if (error && typeof error.message === 'string') {
    const details = Array.isArray(error.details) ? (error.details as ErrorDetail[]) : []
    return new ApiError(status, error.code ?? 'error', error.message, details)
  }
  return new ApiError(status, 'http_error', `Request failed (${status})`)
}

interface Outcome<T> {
  data?: T
  error?: unknown
  response: Response
}

/** The data of a response, or a thrown `ApiError` for anything but success. */
export async function unwrap<T>(outcome: Promise<Outcome<T>>): Promise<T> {
  const { data, error, response } = await outcome
  if (!response.ok) throw toApiError(response.status, error)
  return data as T
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}
