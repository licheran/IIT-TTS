import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { fakeApi } from '@/test/fakeApi'
import { SessionsPage } from './SessionsPage'

const schema = {
  preset: 'academic_weekly',
  kind: 'configured',
  format_version: 2,
  labels: {},
  resource_types: [],
  sheets: [],
}

const row = (over: object = {}) => ({
  code: 'M1-LEC-01',
  module: 'M1',
  kind: 'LEC',
  demand: 'M1-LEC',
  groups: ['P1/G1'],
  teachers: ['T1'],
  rooms: ['R1'],
  day: 'Mon',
  start: 'P1',
  end: 'P2',
  edited: [],
  ...over,
})

function setup(routes: Record<string, unknown>) {
  const api = fakeApi({
    'GET /datasets/4/schema': schema,
    'GET /datasets/4/timetable/check': { run_id: 1, violations: [] },
    ...routes,
  })
  render(
    <MemoryRouter>
      <QueryClientProvider client={new QueryClient()}>
        <SessionsPage datasetId={4} />
      </QueryClientProvider>
    </MemoryRouter>,
  )
  return { api, user: userEvent.setup() }
}

test('before any run the table says to press Start', async () => {
  setup({ 'GET /datasets/4/timetable': { run_id: null, edits: 0, rows: [] } })
  expect(await screen.findByText(/Nothing solved yet: press Start/)).toBeInTheDocument()
})

test('an edited session shows its marks and the banner counts the edits', async () => {
  setup({
    'GET /datasets/4/timetable': {
      run_id: 1,
      edits: 1,
      rows: [row({ edited: ['groups', 'day'] }), row({ code: 'M1-TUT-01', kind: 'TUT' })],
    },
  })
  expect(await screen.findByText('1 edit waiting: press Rebuild.')).toBeInTheDocument()
  const cells = await screen.findAllByRole('gridcell')
  const marked = cells.filter((c) => c.getAttribute('data-edited') === 'true')
  expect(marked.map((c) => c.getAttribute('data-column')).sort()).toEqual(['day', 'groups'])
  expect(screen.getAllByRole('button', { name: /Undo edit of/ })).toHaveLength(1)
})

test('undo forgets one edit and clear forgets them all', async () => {
  const edited = {
    'GET /datasets/4/timetable': { run_id: 1, edits: 2, rows: [row({ edited: ['day'] })] },
    'DELETE /datasets/4/timetable/M1-LEC-01': { run_id: 1, edits: 1, rows: [row()] },
    'DELETE /datasets/4/timetable': { run_id: 1, edits: 0, rows: [row()] },
  }
  const { api, user } = setup(edited)
  await user.click(await screen.findByRole('button', { name: 'Undo edit of M1-LEC-01' }))
  await user.click(await screen.findByRole('button', { name: 'Clear all edits' }))
  const deletes = api.calls.filter((c) => c.method === 'DELETE').map((c) => c.path)
  expect(deletes).toEqual(['/datasets/4/timetable/M1-LEC-01', '/datasets/4/timetable'])
})

test('a clash an edit causes is listed and its session is shown in red', async () => {
  setup({
    'GET /datasets/4/timetable': { run_id: 1, edits: 1, rows: [row({ edited: ['rooms'] })] },
    'GET /datasets/4/timetable/check': {
      run_id: 1,
      violations: [
        {
          code: 'no_overlap',
          constraint_code: 'H1',
          severity: 'hard',
          message: 'R1 is used by M1-LEC-01 and M1-TUT-01 at Mon P1',
          refs: [{ kind: 'event', code: 'M1-LEC-01' }],
        },
      ],
    },
  })
  expect(
    await screen.findByText('Clashes in the timetable with your edits (1)'),
  ).toBeInTheDocument()
  const rows = await screen.findAllByRole('row')
  expect(rows.some((r) => r.getAttribute('title')?.includes('R1 is used by'))).toBe(true)
})
