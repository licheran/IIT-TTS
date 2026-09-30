import type { DataColumn } from '@/components/DataTable'
import type { ColumnDef, SheetDef } from '@/api/types'

/** The referenced sheets of every column of a sheet, without duplicates. */
export function referencedSheets(sheet: SheetDef): string[] {
  return [...new Set(sheet.columns.flatMap((c) => c.refs))]
}

/** The editor kind of a column, from the sheet definition (the UI hard-codes no column). */
export function kindOf(column: ColumnDef | undefined): DataColumn['kind'] {
  if (!column) return 'text'
  if (column.choices.length > 0) return 'choice'
  if (column.kind === 'bool') return 'bool'
  if (column.kind === 'int') return 'int'
  if (column.kind === 'pairs') return 'tags'
  if (column.kind === 'json') return 'json'
  if (column.refs.length > 0) return column.kind === 'list' ? 'multiref' : 'ref'
  return 'text'
}

/**
 * Table columns for the headers the server returned: the sheet's defined columns, then the
 * user's `x_` note columns. `options` maps a sheet name to the codes it holds.
 */
export function buildColumns(
  headers: string[],
  sheet: SheetDef,
  options: Map<string, string[]>,
  labels: Record<string, string> = {},
): DataColumn[] {
  return headers.map((header) => {
    const def = sheet.columns.find((c) => c.name === header)
    const kind = kindOf(def)
    const choices = def?.choices ?? []
    const refs = def?.refs ?? []
    return {
      id: header,
      header: labels[header] || def?.label || header,
      kind,
      required: def?.required ?? false,
      readOnly: def?.derive != null,
      options:
        choices.length > 0
          ? [...choices]
          : [...new Set(refs.flatMap((sheetName) => options.get(sheetName) ?? []))],
      width: kind === 'multiref' || kind === 'tags' || kind === 'json' ? 200 : 140,
    }
  })
}
