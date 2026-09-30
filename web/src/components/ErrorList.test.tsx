import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ErrorList, groupBySheet } from './ErrorList'

const errors = [
  { sheet: 'Rooms', row: 3, text: 'Rooms!R3 [capacity]: not a number' },
  { sheet: 'Teachers', row: 2, text: 'Teachers!R2: duplicate' },
  { sheet: 'Rooms', row: 9, text: 'Rooms!R9: unknown building' },
]

test('problems are grouped by sheet in order of first appearance', () => {
  expect(groupBySheet(errors).map(([sheet, items]) => [sheet, items.length])).toEqual([
    ['Rooms', 2],
    ['Teachers', 1],
  ])
})

test('every problem is listed under its sheet', () => {
  render(<ErrorList title="Nothing was imported" errors={errors} />)
  expect(screen.getByRole('alert')).toHaveTextContent('Nothing was imported (3)')
  expect(screen.getByRole('heading', { name: 'Rooms' })).toBeInTheDocument()
  expect(screen.getAllByRole('listitem')).toHaveLength(3)
})

test('a problem can jump to its row', async () => {
  const onSelect = vi.fn()
  render(<ErrorList errors={errors} onSelect={onSelect} />)
  await userEvent.click(screen.getByRole('button', { name: /R9/ }))
  expect(onSelect).toHaveBeenCalledWith(errors[2])
})

test('nothing is shown without problems', () => {
  const { container } = render(<ErrorList errors={[]} />)
  expect(container).toBeEmptyDOMElement()
})
