import { chosen, isChosen } from './lookup'

test('a single field takes the code that was clicked', () => {
  expect(chosen('GP', 'JV', false)).toBe('JV')
  expect(isChosen(' JV ', 'JV', false)).toBe(true)
  expect(isChosen('GP', 'JV', false)).toBe(false)
})

test('a list field gains a code when it is clicked and loses it when it is clicked again', () => {
  expect(chosen('', 'M1', true)).toBe('M1')
  expect(chosen('M1;M2', 'M3', true)).toBe('M1;M2;M3')
  expect(chosen('M1;M2;M3', 'M2', true)).toBe('M1;M3')
  expect(chosen(' M1 ; ; M2 ', 'M1', true)).toBe('M2')
  expect(isChosen('M1; M2', 'M2', true)).toBe(true)
  expect(isChosen('M1', 'M2', true)).toBe(false)
})
