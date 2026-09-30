import type { ColumnDef, SheetDef } from '@/api/types'
import { buildColumns, kindOf, referencedSheets } from './columns'

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

test('the editor kind follows the sheet definition', () => {
  expect(kindOf(undefined)).toBe('text')
  expect(kindOf(col({ kind: 'int' }))).toBe('int')
  expect(kindOf(col({ kind: 'bool' }))).toBe('bool')
  expect(kindOf(col({ choices: ['a', 'b'] }))).toBe('choice')
  expect(kindOf(col({ refs: ['Rooms'] }))).toBe('ref')
  expect(kindOf(col({ kind: 'list', refs: ['Rooms'] }))).toBe('multiref')
  expect(kindOf(col({ kind: 'pairs' }))).toBe('tags')
  expect(kindOf(col({ kind: 'json' }))).toBe('json')
})

const sheet = {
  name: 'Activities',
  target: 'event',
  label: '',
  export_only: false,
  hidden: false,
  import_only: false,
  columns: [
    col({ name: 'code', required: true }),
    col({ name: 'module', refs: ['Modules'] }),
    col({ name: 'kind', choices: ['LEC', 'TUT'] }),
    col({ name: 'end', derive: 'end' }),
  ],
} as SheetDef

test('columns come from the headers, with options from the referenced sheets', () => {
  const options = new Map([['Modules', ['M1', 'M2']]])
  const columns = buildColumns(['code', 'module', 'kind', 'end', 'x_note'], sheet, options)
  expect(columns.map((c) => c.kind)).toEqual(['text', 'ref', 'choice', 'text', 'text'])
  expect(columns[1]?.options).toEqual(['M1', 'M2'])
  expect(columns[2]?.options).toEqual(['LEC', 'TUT'])
  expect(columns[0]?.required).toBe(true)
  expect(columns[3]?.readOnly).toBe(true)
  expect(columns[4]?.readOnly).toBe(false) // the user's own note column
})

test('the referenced sheets are listed once', () => {
  expect(referencedSheets(sheet)).toEqual(['Modules'])
})
