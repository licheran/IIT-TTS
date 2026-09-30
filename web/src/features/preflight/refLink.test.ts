import { refLink } from './PreflightPanel'

test('a reference links to the row of its sheet', () => {
  expect(refLink(3, { kind: 'resource', code: 'L6 SE / G1', sheet: 'Groups' })).toBe(
    '/datasets/3/tables/Groups?find=L6%20SE%20%2F%20G1',
  )
})

test('a reference with no sheet has no link', () => {
  expect(refLink(3, { kind: 'slot', code: 'Mon:P01', sheet: null })).toBeNull()
})
