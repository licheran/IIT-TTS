import type { RunOut } from '@/api/types'
import { whyNotFinished } from './StartPanel'

const run = (over: Partial<RunOut>): RunOut =>
  ({ id: 1, status: 'failed', progress: {}, diagnostics: [], ...over }) as RunOut

test('the errors of a run are listed and its warnings are not', () => {
  const found = whyNotFinished(
    run({
      diagnostics: [
        {
          kind: 'no_solution',
          severity: 'error',
          message: 'no timetable found',
          refs: [],
          details: [],
          minimal: true,
        },
        {
          kind: 'solver_warning',
          severity: 'warning',
          message: 'ignored',
          refs: [],
          details: [],
          minimal: true,
        },
      ],
    }),
  )
  expect(found).toEqual([{ message: 'no timetable found' }])
})

test('the text of a crash kept in the progress is shown', () => {
  const found = whyNotFinished(run({ progress: { error: 'ValueError: boom' } }))
  expect(found).toEqual([{ message: 'ValueError: boom' }])
})

test('a run with nothing to report lists nothing', () => {
  expect(whyNotFinished(run({ status: 'succeeded' }))).toEqual([])
})
