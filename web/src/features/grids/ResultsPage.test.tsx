import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import type { SchemaOut } from '@/api/types'
import { fakeApi } from '@/test/fakeApi'
import { ResultsPage } from './ResultsPage'

const schema = {
  preset: 'p',
  format_version: 1,
  labels: { StudentGroup: 'Group', Teacher: 'Teacher' },
  resource_types: [],
  sheets: [
    {
      name: 'Groups',
      target: 'resource',
      resource_type: 'StudentGroup',
      label: 'Groups',
      export_only: false,
      hidden: false,
      import_only: false,
      columns: [],
    },
    {
      name: 'Teachers',
      target: 'resource',
      resource_type: 'Teacher',
      label: 'Teachers',
      export_only: false,
      hidden: false,
      import_only: false,
      columns: [],
    },
  ],
} as unknown as SchemaOut

const run = { id: 7, dataset_id: 1, status: 'succeeded', published: false }

test('the timetable tab links to a single grid, a type, every timetable and Excel', async () => {
  fakeApi({
    'GET /datasets/1/schema': schema,
    'GET /datasets/1/runs': [run],
    'GET /datasets/1/tables/Groups': {
      sheet: 'Groups',
      headers: ['code'],
      total: 1,
      page: 1,
      size: 10000,
      rows: [{ key: 'G1', values: { code: 'G1' } }],
    },
    'GET /runs/7/grid': { cells: [], days: [], periods: [] },
  })
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <MemoryRouter>
        <ResultsPage datasetId={1} />
      </MemoryRouter>
    </QueryClientProvider>,
  )
  const href = async (name: string) =>
    new URL((await screen.findByRole('link', { name })).getAttribute('href')!).search
  expect(await href('Export this grid (HTML)')).toBe('?format=html&type=StudentGroup&code=G1')
  expect(await href('Export all of this type (HTML)')).toBe('?format=html&type=StudentGroup')
  expect(await href('Export all timetables (HTML)')).toBe('?format=html')
  expect(await href('Export all (Excel)')).toBe('?format=xlsx')
})
