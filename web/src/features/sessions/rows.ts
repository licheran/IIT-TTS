import type { DataRow } from '@/components/DataTable'
import type { DraftViolation, EditBody, SessionOut } from '@/api/types'

/** The table columns that hold a list of resources, by column id. */
const LIST_COLUMNS = ['groups', 'teachers', 'rooms'] as const

/** The rows of the Activities table of a configured dataset, one per session. */
export function sessionRows(sessions: SessionOut[], violations: DraftViolation[] = []): DataRow[] {
  const problems = new Map<string, string[]>()
  for (const v of violations) {
    for (const ref of v.refs) {
      if (ref.kind !== 'event' || !ref.code) continue
      problems.set(ref.code, [...(problems.get(ref.code) ?? []), v.message])
    }
  }
  return sessions.map((s) => ({
    key: s.code,
    values: {
      code: s.code,
      module: s.module,
      kind: s.kind,
      groups: s.groups.join(';'),
      teachers: s.teachers.join(';'),
      rooms: s.rooms.join(';'),
      day: s.day,
      start: s.start,
      end: s.end,
    },
    marks: s.edited,
    problem: problems.has(s.code) ? problems.get(s.code)!.join('\n') : undefined,
  }))
}

/** The edit that one changed cell stands for, or a message saying why it cannot be kept. */
export function editOf(column: string, value: string | number | boolean | null): EditBody {
  const text = value === null ? '' : String(value)
  if ((LIST_COLUMNS as readonly string[]).includes(column)) {
    const items = text
      .split(';')
      .map((t) => t.trim())
      .filter((t) => t !== '')
    if (column === 'groups' && items.length === 0) throw new Error('A session needs a group')
    return { [column]: items }
  }
  if (column === 'day' || column === 'start') {
    if (text === '') throw new Error('Choose a value, or use "Undo edit" to go back to the run')
    return { [column]: text }
  }
  throw new Error(`The ${column} column cannot be edited`)
}

/** How many sessions carry an edit. */
export const editCount = (sessions: SessionOut[]): number =>
  sessions.filter((s) => s.edited.length > 0).length
