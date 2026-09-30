import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ColumnDef, SheetDef } from '@/api/types'
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
  stored_as: [],
  ...over,
})

const rooms = {
  name: 'Rooms',
  target: 'resource',
  resource_type: 'Room',
  label: 'Rooms',
  export_only: false,
  hidden: false,
  import_only: false,
  columns: [
    col({ name: 'code', required: true }),
    col({ name: 'building', refs: ['Buildings'] }),
    col({ name: 'capacity', kind: 'int' }),
  ],
} as SheetDef

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
      <SheetEditor datasetId={1} sheet={rooms} />
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

const entryRoom = () => ({
  'GET /datasets/1/tables/Rooms': roomRows,
  'GET /datasets/1/tables/Buildings': buildingRows,
})

test('the entry row is always visible, with no button to open it', async () => {
  fakeApi(entryRoom())
  renderEditor()
  await screen.findByText('60')
  expect(screen.queryByRole('button', { name: 'Add row' })).not.toBeInTheDocument()
  const row = screen.getByRole('row', { name: 'New row for Rooms' })
  expect(within(row).getByLabelText('New code (required)')).toBeInTheDocument()
  expect(within(row).getByLabelText('New building')).toBeInTheDocument()
})

test('Tab moves across the entry fields without adding the row', async () => {
  const api = fakeApi(entryRoom())
  renderEditor()
  await screen.findByText('60')
  const user = userEvent.setup()
  await user.click(screen.getByLabelText('New code (required)'))
  await user.keyboard('R3{Tab}GP{Tab}45')
  expect(screen.getByLabelText('New capacity')).toHaveFocus()
  expect(screen.getByLabelText('New code (required)')).toHaveValue('R3')
  expect(api.calls.some((c) => c.method === 'POST')).toBe(false)
})

test('Enter adds the row, clears the fields and returns focus to the first one', async () => {
  const api = fakeApi({ ...entryRoom(), 'POST /datasets/1/tables/Rooms': { key: 'R3' } })
  renderEditor()
  await screen.findByText('60')
  const user = userEvent.setup()
  await user.click(screen.getByLabelText('New code (required)'))
  await user.keyboard('R3{Tab}{Tab}45{Enter}')
  await vi.waitFor(() => expect(api.calls.filter((c) => c.method === 'POST')).toHaveLength(1))
  expect(api.calls.find((c) => c.method === 'POST')?.body).toEqual({
    values: { code: 'R3', capacity: 45 },
  })
  await vi.waitFor(() => expect(screen.getByLabelText('New code (required)')).toHaveFocus())
  expect(screen.getByLabelText('New code (required)')).toHaveValue('')
  expect(screen.getByLabelText('New capacity')).toHaveValue(null)

  await user.keyboard('R4{Enter}')
  await vi.waitFor(() => expect(api.calls.filter((c) => c.method === 'POST')).toHaveLength(2))
  expect(api.calls.filter((c) => c.method === 'POST')[1]?.body).toEqual({ values: { code: 'R4' } })
})

test('Enter on an empty entry row adds nothing', async () => {
  const api = fakeApi(entryRoom())
  renderEditor()
  await screen.findByText('60')
  const user = userEvent.setup()
  await user.click(screen.getByLabelText('New code (required)'))
  await user.keyboard('{Enter}')
  expect(api.calls.some((c) => c.method === 'POST')).toBe(false)
})

test('a refused row keeps what was typed, shows the problem and focuses the field', async () => {
  fakeApi({
    ...entryRoom(),
    'POST /datasets/1/tables/Rooms': () =>
      new Response(
        JSON.stringify({
          error: {
            code: 'invalid_table',
            message: 'the change is not valid',
            details: [
              { sheet: 'Rooms', row: 4, text: 'Rooms!R4 [building]: unknown building "X"' },
            ],
          },
        }),
        { status: 422, headers: { 'content-type': 'application/json' } },
      ),
  })
  renderEditor()
  await screen.findByText('60')
  const user = userEvent.setup()
  await user.click(screen.getByLabelText('New code (required)'))
  await user.keyboard('R3{Tab}X{Enter}')
  const alert = await screen.findByRole('alert', { name: 'the change is not valid' })
  expect(within(alert).getByText(/unknown building "X"/)).toBeInTheDocument()
  await vi.waitFor(() => expect(screen.getByLabelText('New building')).toHaveFocus())
  expect(screen.getByLabelText('New code (required)')).toHaveValue('R3')
  expect(screen.getByLabelText('New building')).toHaveValue('X')
})

test('a number that is not whole is refused before anything is sent', async () => {
  const api = fakeApi(entryRoom())
  renderEditor()
  await screen.findByText('60')
  const user = userEvent.setup()
  await user.click(screen.getByLabelText('New code (required)'))
  await user.keyboard('R3{Tab}{Tab}4.5{Enter}')
  expect(await screen.findByText(/is not a whole number/)).toBeInTheDocument()
  expect(api.calls.some((c) => c.method === 'POST')).toBe(false)
})

test('Escape clears the entry row', async () => {
  fakeApi(entryRoom())
  renderEditor()
  await screen.findByText('60')
  const user = userEvent.setup()
  await user.click(screen.getByLabelText('New code (required)'))
  await user.keyboard('R3{Tab}GP{Escape}')
  expect(screen.getByLabelText('New code (required)')).toHaveValue('')
  expect(screen.getByLabelText('New building')).toHaveValue('')
})

test('Enter in the entry row does not open the grid cell editor', async () => {
  fakeApi(entryRoom())
  renderEditor()
  await screen.findByText('60')
  const user = userEvent.setup()
  await user.click(screen.getByLabelText('New code (required)'))
  await user.keyboard('{Enter}')
  expect(screen.queryByLabelText('code of R1')).not.toBeInTheDocument()
})
