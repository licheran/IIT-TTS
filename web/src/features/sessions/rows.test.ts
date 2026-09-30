import { describe, expect, it } from 'vitest'
import type { DraftViolation, SessionOut } from '@/api/types'
import { editCount, editOf, sessionRows } from './rows'

const session = (over: Partial<SessionOut> = {}): SessionOut => ({
  code: 'M1-LEC-01',
  module: 'M1',
  kind: 'LEC',
  demand: 'M1-LEC',
  groups: ['P1/G1', 'P1/G2'],
  teachers: ['T1'],
  rooms: ['R1'],
  day: 'Mon',
  start: 'P1',
  end: 'P2',
  edited: [],
  ...over,
})

describe('sessionRows', () => {
  it('shows one row per session with its lists joined by semicolons', () => {
    const [row] = sessionRows([session()])
    expect(row!.key).toBe('M1-LEC-01')
    expect(row!.values.groups).toBe('P1/G1;P1/G2')
    expect(row!.values.day).toBe('Mon')
    expect(row!.marks).toEqual([])
    expect(row!.problem).toBeUndefined()
  })

  it('marks the edited fields', () => {
    const [row] = sessionRows([session({ edited: ['groups', 'day'] })])
    expect(row!.marks).toEqual(['groups', 'day'])
  })

  it('puts a clash on the sessions it names, and on no other', () => {
    const clash: DraftViolation = {
      code: 'no_overlap',
      constraint_code: 'H1',
      severity: 'hard',
      message: 'R1 is used twice at Mon P1',
      refs: [
        { kind: 'resource', code: 'R1' },
        { kind: 'event', code: 'M1-LEC-01' },
      ],
    }
    const rows = sessionRows([session(), session({ code: 'M1-TUT-01' })], [clash])
    expect(rows[0]!.problem).toBe('R1 is used twice at Mon P1')
    expect(rows[1]!.problem).toBeUndefined()
  })
})

describe('editOf', () => {
  it('turns a list cell into a list', () => {
    expect(editOf('rooms', 'R1; R2')).toEqual({ rooms: ['R1', 'R2'] })
    expect(editOf('teachers', null)).toEqual({ teachers: [] })
  })

  it('keeps a day or a start as text', () => {
    expect(editOf('day', 'Fri')).toEqual({ day: 'Fri' })
    expect(editOf('start', 'P3')).toEqual({ start: 'P3' })
  })

  it('refuses an empty day, start or group list, and a column that is not editable', () => {
    expect(() => editOf('day', null)).toThrow(/Undo edit/)
    expect(() => editOf('groups', '')).toThrow(/needs a group/)
    expect(() => editOf('end', 'P3')).toThrow(/cannot be edited/)
  })
})

describe('editCount', () => {
  it('counts the sessions with an edited field', () => {
    expect(editCount([session(), session({ edited: ['day'] })])).toBe(1)
  })
})
