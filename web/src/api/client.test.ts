import { ApiError, toApiError, unwrap } from './client'

test('the standard error shape becomes an ApiError with its details', () => {
  const error = toApiError(422, {
    error: {
      code: 'invalid_table',
      message: 'the change is not valid',
      details: [{ sheet: 'Rooms', row: 2, message: 'unknown building', text: 'Rooms!R2: unknown' }],
    },
  })
  expect(error).toBeInstanceOf(ApiError)
  expect(error.code).toBe('invalid_table')
  expect(error.details[0]?.sheet).toBe('Rooms')
})

test('an unexpected body still gives a readable error', () => {
  expect(toApiError(500, 'oops').message).toBe('Request failed (500)')
})

test('unwrap returns data and throws on a failed response', async () => {
  const ok = await unwrap(
    Promise.resolve({ data: { a: 1 }, response: new Response(null, { status: 200 }) }),
  )
  expect(ok).toEqual({ a: 1 })
  await expect(
    unwrap(
      Promise.resolve({
        error: { error: { code: 'not_found', message: 'no such run' } },
        response: new Response(null, { status: 404 }),
      }),
    ),
  ).rejects.toMatchObject({ status: 404, code: 'not_found', message: 'no such run' })
})
