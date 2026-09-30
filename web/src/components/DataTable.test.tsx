import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DataTable, parseDraft, type DataColumn, type DataRow } from './DataTable'
import { formatPairs, parsePairs, splitList } from './editors'

const columns: DataColumn[] = [
  { id: 'code', header: 'code', kind: 'text', readOnly: true, required: true },
  { id: 'capacity', header: 'capacity', kind: 'int' },
  { id: 'active', header: 'active', kind: 'bool' },
]
const rows: DataRow[] = [
  { key: 'B', values: { code: 'B', capacity: 40, active: false } },
  { key: 'A', values: { code: 'A', capacity: 120, active: true } },
  { key: 'C', values: { code: 'C', capacity: null, active: false } },
]

function setup(onEdit = vi.fn(), onDelete = vi.fn()) {
  render(
    <DataTable label="Rooms" columns={columns} rows={rows} onEdit={onEdit} onDelete={onDelete} />,
  )
  return { onEdit, onDelete, user: userEvent.setup() }
}

const bodyRows = () => screen.getAllByRole('row').slice(1)

test('renders every row and its cells', () => {
  setup()
  expect(bodyRows()).toHaveLength(3)
  expect(within(bodyRows()[1]!).getByText('120')).toBeInTheDocument()
})

test('sorts by a column when its header is clicked', async () => {
  const { user } = setup()
  await user.click(screen.getByRole('button', { name: /^code/ }))
  expect(bodyRows().map((r) => r.getAttribute('data-key'))).toEqual(['A', 'B', 'C'])
  await user.click(screen.getByRole('button', { name: /^code/ }))
  expect(bodyRows().map((r) => r.getAttribute('data-key'))).toEqual(['C', 'B', 'A'])
  expect(screen.getByRole('columnheader', { name: /code/ })).toHaveAttribute(
    'aria-sort',
    'descending',
  )
})

test('filters rows by any cell', async () => {
  const { user } = setup()
  await user.type(screen.getByLabelText('Filter rows'), '120')
  expect(bodyRows()).toHaveLength(1)
  expect(screen.getByText('1 of 3 rows')).toBeInTheDocument()
})

test('moves between cells with the arrow keys and edits with Enter', async () => {
  const { user, onEdit } = setup()
  screen.getByRole('grid').focus()
  await user.keyboard('{ArrowRight}{Enter}')
  const input = screen.getByLabelText('capacity of B')
  await user.clear(input)
  await user.type(input, '55{Enter}')
  expect(onEdit).toHaveBeenCalledWith('B', 'capacity', 55)
})

test('Escape cancels an edit without saving', async () => {
  const { user, onEdit } = setup()
  screen.getByRole('grid').focus()
  await user.keyboard('{ArrowRight}{Enter}')
  await user.type(screen.getByLabelText('capacity of B'), '9{Escape}')
  expect(onEdit).not.toHaveBeenCalled()
  expect(screen.queryByLabelText('capacity of B')).not.toBeInTheDocument()
})

test('a read-only cell cannot be edited', async () => {
  const { user, onEdit } = setup()
  screen.getByRole('grid').focus()
  await user.keyboard('{Enter}')
  expect(screen.queryByLabelText('code of B')).not.toBeInTheDocument()
  expect(onEdit).not.toHaveBeenCalled()
})

test('a boolean cell toggles on Enter', async () => {
  const { user, onEdit } = setup()
  screen.getByRole('grid').focus()
  await user.keyboard('{ArrowRight}{ArrowRight}{Enter}')
  expect(onEdit).toHaveBeenCalledWith('B', 'active', true)
})

test('a bad number is refused and the editor stays open', async () => {
  const { user, onEdit } = setup()
  screen.getByRole('grid').focus()
  await user.keyboard('{ArrowRight}{Enter}')
  const input = screen.getByLabelText('capacity of B')
  await user.clear(input)
  await user.type(input, '1.5{Enter}')
  expect(await screen.findByRole('alert')).toHaveTextContent('not a whole number')
  expect(onEdit).not.toHaveBeenCalled()
})

test('a failed save keeps the editor open and shows the message', async () => {
  const { user } = setup(vi.fn().mockRejectedValue(new Error('unknown room')))
  screen.getByRole('grid').focus()
  await user.keyboard('{ArrowRight}{Enter}')
  const input = screen.getByLabelText('capacity of B')
  await user.clear(input)
  await user.type(input, '7{Enter}')
  expect(await screen.findByRole('alert')).toHaveTextContent('unknown room')
})

test('deletes a row after confirmation', async () => {
  vi.spyOn(window, 'confirm').mockReturnValue(true)
  const { user, onDelete } = setup()
  await user.click(screen.getByRole('button', { name: 'Delete row A' }))
  expect(onDelete).toHaveBeenCalledWith('A')
})

test('parseDraft turns text into cell values', () => {
  expect(parseDraft('', 'int')).toBeNull()
  expect(parseDraft('12', 'int')).toBe(12)
  expect(parseDraft('x', 'text')).toBe('x')
  expect(() => parseDraft('{', 'json')).toThrow(/JSON/)
})

test('list and tag text round-trips', () => {
  expect(splitList('a; b;;c')).toEqual(['a', 'b', 'c'])
  expect(parsePairs('room_type=lab;floor=2')).toEqual([
    ['room_type', 'lab'],
    ['floor', '2'],
  ])
  expect(formatPairs(parsePairs('room_type=lab;floor=2'))).toBe('room_type=lab;floor=2')
})
