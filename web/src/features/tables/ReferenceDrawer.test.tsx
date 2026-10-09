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
  suggests: [],
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

const buildings = {
  sheet: 'Buildings',
  headers: ['code', 'name', 'campus'],
  total: 3,
  page: 1,
  size: 10000,
  rows: [
    { key: 'GP', values: { code: 'GP', name: 'Galle Park', campus: 'MAIN' } },
    { key: 'JV', values: { code: 'JV', name: 'Java', campus: 'MAIN' } },
    { key: 'RM', values: { code: 'RM', name: 'Rama', campus: 'NORTH' } },
  ],
}

const routes = {
  'GET /datasets/1/tables/Rooms': roomRows,
  'GET /datasets/1/tables/Buildings': buildings,
  'PATCH /datasets/1/tables/Rooms/R1': { key: 'R1' },
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

async function editBuildingOfR1(user: ReturnType<typeof userEvent.setup>) {
  await screen.findByText('60')
  screen.getByRole('grid', { name: 'Rooms' }).focus()
  await user.keyboard('{ArrowRight}{Enter}')
  return screen.getByLabelText('building of R1')
}

const lookupButton = () => screen.getByRole('button', { name: 'Look up building of R1' })
const drawer = () => screen.findByRole('dialog', { name: 'building of R1' })

test('the lookup of a reference cell shows the target table with all its columns', async () => {
  fakeApi(routes)
  renderEditor()
  const user = userEvent.setup()
  await editBuildingOfR1(user)
  await user.click(lookupButton())
  const panel = await drawer()
  expect(within(panel).getByRole('columnheader', { name: 'campus' })).toBeInTheDocument()
  expect(await within(panel).findByText('Galle Park')).toBeInTheDocument()
  expect(within(panel).getByText('3 rows')).toBeInTheDocument()
})

test('the search of the lookup looks in every column', async () => {
  fakeApi(routes)
  renderEditor()
  const user = userEvent.setup()
  await editBuildingOfR1(user)
  await user.click(lookupButton())
  const panel = await drawer()
  await within(panel).findByText('Galle Park')
  await user.type(within(panel).getByLabelText('Search the table'), 'north')
  expect(within(panel).getByText('1 row')).toBeInTheDocument()
  expect(within(panel).getByText('Rama')).toBeInTheDocument()
  expect(within(panel).queryByText('Java')).not.toBeInTheDocument()
})

test('a click on a row puts its code in the field and closes the lookup, and Enter saves it', async () => {
  const api = fakeApi(routes)
  renderEditor()
  const user = userEvent.setup()
  await editBuildingOfR1(user)
  await user.click(lookupButton())
  const panel = await drawer()
  await user.click(await within(panel).findByRole('row', { name: 'Choose JV' }))
  expect(screen.queryByRole('dialog', { name: 'building of R1' })).not.toBeInTheDocument()
  expect(screen.getByLabelText('building of R1')).toHaveValue('JV')
  expect(api.calls.some((c) => c.method === 'PATCH')).toBe(false) // nothing saved yet
  await user.keyboard('{Enter}')
  await vi.waitFor(() =>
    expect(api.calls.find((c) => c.method === 'PATCH')?.body).toEqual({
      values: { building: 'JV' },
    }),
  )
})

test('Ctrl+Space opens the lookup, and Escape closes it before it cancels the edit', async () => {
  fakeApi(routes)
  renderEditor()
  const user = userEvent.setup()
  await editBuildingOfR1(user)
  await user.keyboard('{Control>} {/Control}')
  expect(await drawer()).toBeInTheDocument()
  await user.keyboard('{Escape}')
  await vi.waitFor(() =>
    expect(screen.queryByRole('dialog', { name: 'building of R1' })).not.toBeInTheDocument(),
  )
  expect(screen.getByLabelText('building of R1')).toBeInTheDocument() // still editing
  await user.keyboard('{Escape}')
  expect(screen.queryByLabelText('building of R1')).not.toBeInTheDocument()
})

test('using the lookup does not save what was typed', async () => {
  const api = fakeApi(routes)
  renderEditor()
  const user = userEvent.setup()
  const field = await editBuildingOfR1(user)
  await user.clear(field)
  await user.type(field, 'J')
  await user.click(lookupButton())
  await drawer()
  await user.type(screen.getByLabelText('Search the table'), 'rama')
  expect(api.calls.some((c) => c.method === 'PATCH')).toBe(false)
  expect(screen.getByRole('combobox', { name: 'building of R1' })).toHaveValue('J')
})
