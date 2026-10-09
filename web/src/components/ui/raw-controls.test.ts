import { describe, expect, it } from 'vitest'

// ADR-0009: a form control is one of the components of `components/ui/`, so the controls look
// and measure the same everywhere. A raw element is allowed only where the thing is not a form
// control of the page: the table's own editors and header, the timetable's event cells, and a
// link-like button in a list. Each exception says why.
const ALLOWED: Record<string, string> = {
  'components/editors.tsx': 'the cell editors of the table',
  'components/DataTable.tsx': 'the sortable column header',
  'features/grids/GridView.tsx': 'an event of the timetable grid',
  'components/ErrorList.tsx': 'a list entry that looks like a link',
  'features/tables/ReferenceDrawer.tsx': 'the rows and tabs of the lookup, which act as buttons',
}

const RAW = /<(input|select|button|textarea)\b/

// Every component source (not the tests), by its path below `src/`.
const files = Object.fromEntries(
  Object.entries(
    import.meta.glob(['/src/**/*.tsx', '!/src/**/*.test.tsx'], {
      query: '?raw',
      import: 'default',
      eager: true,
    }) as Record<string, string>,
  ).map(([path, text]) => [path.replace('/src/', ''), text]),
)

describe('raw form controls', () => {
  it('finds the sources', () => {
    expect(Object.keys(files)).toContain('components/ui/button.tsx')
  })

  it('appear only in components/ui and the listed exceptions', () => {
    const offenders = Object.keys(files).filter(
      (file) => !file.startsWith('components/ui/') && !(file in ALLOWED) && RAW.test(files[file]!),
    )
    expect(offenders).toEqual([])
  })

  it('has no exception that no longer needs one', () => {
    for (const file of Object.keys(ALLOWED)) {
      expect(RAW.test(files[file] ?? ''), file).toBe(true)
    }
  })

  it('sets no control height of its own outside components/ui', () => {
    const offenders = Object.keys(files).filter(
      (file) => !file.startsWith('components/ui/') && /\bh-(7|8|9|10)\b/.test(files[file]!),
    )
    expect(offenders).toEqual([])
  })
})
