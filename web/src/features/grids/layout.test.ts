import { placement } from './layout'

test('a two-period event is one block of two rows', () => {
  expect(placement({ row: 2, span: 2, day_index: 1, lane: 0, lanes: 1 })).toEqual({
    gridRow: '4 / span 2',
    gridColumn: 3,
    widthPercent: 100,
    leftPercent: 0,
  })
})

test('overlapping events share the day column side by side', () => {
  const first = placement({ row: 0, span: 2, day_index: 0, lane: 0, lanes: 3 })
  const third = placement({ row: 0, span: 2, day_index: 0, lane: 2, lanes: 3 })
  expect(first.widthPercent).toBeCloseTo(33.33, 1)
  expect(third.leftPercent).toBeCloseTo(66.67, 1)
})

test('a span is at least one row', () => {
  expect(placement({ row: 0, span: 0, day_index: 0, lane: 0, lanes: 0 }).gridRow).toBe('2 / span 1')
})
