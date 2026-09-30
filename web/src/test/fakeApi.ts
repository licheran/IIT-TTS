/** A fake API for component tests: routes are "METHOD /path" (query string ignored). */

export type Handler = unknown | ((request: { url: URL; body: unknown }) => unknown)

export interface FakeApi {
  calls: { method: string; path: string; body: unknown }[]
}

export function fakeApi(routes: Record<string, Handler>): FakeApi {
  const api: FakeApi = { calls: [] }
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: Request | string, init?: RequestInit) => {
      const request = typeof input === 'string' ? new Request(input, init) : input
      const url = new URL(request.url)
      const path = url.pathname.replace(/^\/api/, '')
      const text = request.method === 'GET' ? '' : await request.text()
      const body = text ? JSON.parse(text) : undefined
      api.calls.push({ method: request.method, path, body })
      const handler = routes[`${request.method} ${path}`] ?? routes[`${request.method} *`]
      if (handler === undefined) {
        return new Response(
          JSON.stringify({ error: { code: 'not_found', message: `no route ${path}` } }),
          {
            status: 404,
            headers: { 'content-type': 'application/json' },
          },
        )
      }
      const value = typeof handler === 'function' ? handler({ url, body }) : handler
      if (value instanceof Response) return value
      if (value === null) return new Response(null, { status: 204 })
      return new Response(JSON.stringify(value), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      })
    }),
  )
  return api
}
