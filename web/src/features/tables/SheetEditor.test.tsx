import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ColumnDef, SchemaOut, SheetDef } from '@/api/types'
import { fakeApi } from '@/test/fakeApi'
import { SheetEditor } from './SheetEditor'

const col = (over: Partial<ColumnDef>): ColumnDef => ({
  name: 'x',
  field: 'x',
  kind: 'str',
  required: false,
  refs: [],
  allow_star: false,
  choices: [],
  label: '',
  ...over,
})

const rooms = {
  name: 'Rooms',
  target: 'resource',
  resource_type: 'Room',
  label: 'Rooms',
  export_only: false,
  columns: [
    col({ name: 'code', required: true }),
    col({ name: 'building', refs: ['Buildings'] }),
    col({ name: 'capacity', kind: 'int' }),
  ],
} as SheetDef
const schema = {
  preset: 'p',
  format_version: 1,
  sheets: [rooms],
  labels: {},
  resource_types: [],
} as SchemaOut

const roomRows = {
  sheet: 'Rooms',
  headers: ['code', 'building', 'capacity'],
  total: 2,
  page: 1,
  size: 10000,
  rows: [
    { key: 'R1', values: { code: 'R1', building: 'GP', capacity: 30 } },
    { key: 'R2', values: { code: 'R2', building: 'GP', capacity: 60 } },
  ],
}
const buildingRows = {
  sheet: 'Buildings',
  headers: ['code'],
  total: 1,
  page: 1,
  size: 10000,
  rows: [{ key: 'GP', values: { code: 'GP' } }],
}

function renderEditor() {
  return render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <SheetEditor datasetId={1} sheet={rooms} schema={schema} />
    </QueryClientProvider>,
  )
}

test('shows the rows the server returned', async () => {
  fakeApi({
    'GET /datasets/1/tables/Rooms': roomRows,
    'GET /datasets/1/tables/Buildings': buildingRows,
  })
  renderEditor()
  expect(await screen.findByText('60')).toBeInTheDocument()
  expect(screen.getByText('2 rows')).toBeInTheDocument()
})

test('editing a cell sends only that column to the server', async () => {
  const api = fakeApi({
    'GET /datasets/1/tables/Rooms': roomRows,
    'GET /datasets/1/tables/Buildings': buildingRows,
    'PATCH /datasets/1/tables/Rooms/R1': { key: 'R1' },
  })
  renderEditor()
  await screen.findByText('60')
  const user = userEvent.setup()
  screen.getByRole('grid', { name: 'Rooms' }).focus()
  await user.keyboard('{ArrowRight}{ArrowRight}{Enter}')
  const input = screen.getByLabelText('capacity of R1')
  await user.clear(input)
  await user.type(input, '77{Enter}')
  await vi.waitFor(() =>
    expect(api.calls.some((c) => c.method === 'PATCH' && c.path.endsWith('/Rooms/R1'))).toBe(true),
  )
  expect(api.calls.find((c) => c.method === 'PATCH')?.body).toEqual({ values: { capacity: 77 } })
})

test('row-level problems from the server are listed and the edit stays open', async () => {
  fakeApi({
    'GET /datasets/1/tables/Rooms': roomRows,
    'GET /datasets/1/tables/Buildings': buildingRows,
    'PATCH /datasets/1/tables/Rooms/R1': () =>
      new Response(
        JSON.stringify({
          error: {
            code: 'invalid_table',
            message: 'the change is not valid',
            details: [
              { sheet: 'Rooms', row: 2, text: 'Rooms!R2 [building]: unknown building "X"' },
            ],
          },
        }),
        { status: 422, headers: { 'content-type': 'application/json' } },
      ),
  })
  renderEditor()
  await screen.findByText('60')
  const user = userEvent.setup()
  screen.getByRole('grid', { name: 'Rooms' }).focus()
  await user.keyboard('{ArrowRight}{Enter}')
  const input = screen.getByLabelText('building of R1')
  await user.clear(input)
  await user.type(input, 'X{Enter}')
  const alert = await screen.findByRole('alert', { name: 'the change is not valid' })
  expect(within(alert).getByText(/unknown building "X"/)).toBeInTheDocument()
  expect(screen.getByLabelText('building of R1')).toBeInTheDocument()
})

test('a new row is added through the form', async () => {
  const api = fakeApi({
    'GET /datasets/1/tables/Rooms': roomRows,
    'GET /datasets/1/tables/Buildings': buildingRows,
    'POST /datasets/1/tables/Rooms': { key: 'R3' },
  })
  renderEditor()
  await screen.findByText('60')
  const user = userEvent.setup()
  await user.click(screen.getByRole('button', { name: 'Add row' }))
  const form = screen.getByRole('form', { name: 'Add a row to Rooms' })
  await user.type(within(form).getByLabelText(/^code/), 'R3')
  await user.type(within(form).getByLabelText('capacity'), '45')
  await user.click(within(form).getByRole('button', { name: 'Add' }))
  await vi.waitFor(() => expect(api.calls.some((c) => c.method === 'POST')).toBe(true))
  expect(api.calls.find((c) => c.method === 'POST')?.body).toEqual({
    values: { code: 'R3', capacity: 45 },
  })
})
