import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from '@tanstack/react-table'
import { useVirtualizer } from '@tanstack/react-virtual'
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import {
  ChoiceEditor,
  JsonEditor,
  MultiRefSelect,
  RefSelect,
  TagEditor,
  TextEditor,
  jsonProblem,
  type EditorProps,
} from '@/components/editors'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export type CellValue = string | number | boolean | null
export type ColumnKind = 'text' | 'int' | 'bool' | 'choice' | 'ref' | 'multiref' | 'tags' | 'json'

export interface DataColumn {
  id: string
  header: string
  kind: ColumnKind
  width?: number
  readOnly?: boolean
  required?: boolean
  options?: string[]
  /** The value a new row starts with (only used for true/false columns). */
  defaultValue?: CellValue
}

export interface DataRow {
  key: string
  values: Record<string, CellValue>
}

export const ROW_HEIGHT = 34
const HEADER_ONLY = 34
const HEADER_WITH_ENTRY = 82

export function display(value: CellValue | undefined, kind: ColumnKind): string {
  if (value === null || value === undefined) return ''
  if (kind === 'bool') return value === true ? '✓' : ''
  return String(value)
}

/** The text an editor starts with for a cell's value. */
export function draftOf(value: CellValue | undefined): string {
  if (value === null || value === undefined) return ''
  return String(value)
}

/** Turn an editor's text back into a cell value, or throw a message the user can read. */
export function parseDraft(draft: string, kind: ColumnKind): CellValue {
  if (kind === 'bool') return draft === 'true'
  if (draft.trim() === '') return null
  if (kind === 'int') {
    const n = Number(draft)
    if (!Number.isInteger(n)) throw new Error(`"${draft}" is not a whole number`)
    return n
  }
  if (kind === 'json') {
    const problem = jsonProblem(draft)
    if (problem) throw new Error(`Not valid JSON: ${problem}`)
  }
  return draft
}

export const POPOVER_KINDS: ColumnKind[] = ['multiref', 'tags', 'json']

/** The editor for a column kind. Shared by the table's cells and the "add row" form. */
export function EditorFor({
  column,
  ...props
}: EditorProps & { column: Pick<DataColumn, 'kind' | 'options'> }) {
  const shared = { ...props, options: column.options }
  switch (column.kind) {
    case 'int':
      return <TextEditor {...shared} numeric />
    case 'choice':
      return <ChoiceEditor {...shared} />
    case 'ref':
      return <RefSelect {...shared} />
    case 'multiref':
      return <MultiRefSelect {...shared} />
    case 'tags':
      return <TagEditor {...shared} />
    case 'json':
      return <JsonEditor {...shared} />
    default:
      return <TextEditor {...shared} />
  }
}

interface Props {
  label: string
  columns: DataColumn[]
  rows: DataRow[]
  onEdit: (key: string, column: string, value: CellValue) => Promise<unknown> | void
  onDelete?: (key: string) => Promise<unknown> | void
  actions?: ReactNode
  /** A row pinned under the headers, given the grid template so its cells line up. */
  renderEntry?: (layout: { template: string }) => ReactNode
  highlightKey?: string | null
  height?: number
}

export function DataTable({
  label,
  columns,
  rows,
  onEdit,
  onDelete,
  actions,
  renderEntry,
  highlightKey,
  height = 520,
}: Props) {
  const [sorting, setSorting] = useState<SortingState>([])
  const [filter, setFilter] = useState('')
  const [active, setActive] = useState({ r: 0, c: 0 })
  const [editing, setEditing] = useState<{ key: string; column: string; draft: string } | null>(
    null,
  )
  const [error, setError] = useState<string | null>(null)
  const scroller = useRef<HTMLDivElement>(null)
  const finishing = useRef(false)

  const defs = useMemo<ColumnDef<DataRow>[]>(
    () =>
      columns.map((c) => ({
        id: c.id,
        header: c.header,
        accessorFn: (row) => row.values[c.id] ?? null,
        sortUndefined: 'last' as const,
      })),
    [columns],
  )
  const table = useReactTable({
    data: rows,
    columns: defs,
    state: { sorting, globalFilter: filter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    globalFilterFn: (row, _id, value: string) => {
      const needle = value.toLowerCase()
      return Object.values(row.original.values).some(
        (v) => v !== null && String(v).toLowerCase().includes(needle),
      )
    },
  })
  const visible = table.getRowModel().rows
  const virtual = useVirtualizer({
    count: visible.length,
    getScrollElement: () => scroller.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 8,
    scrollPaddingStart: renderEntry ? HEADER_WITH_ENTRY : HEADER_ONLY,
  })

  const template = `${columns
    .map((c) => `minmax(${c.width ?? 140}px, 1fr)`)
    .join(' ')}${onDelete ? ' 72px' : ''}`
  const lastColumn = columns.length - 1

  useEffect(() => {
    if (!highlightKey) return
    const at = visible.findIndex((r) => r.original.key === highlightKey)
    if (at >= 0) {
      setActive((a) => ({ ...a, r: at }))
      virtual.scrollToIndex(at, { align: 'center' })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [highlightKey, rows])

  const commit = async (draftOverride?: string) => {
    if (!editing || finishing.current) return
    const column = columns.find((c) => c.id === editing.column)
    if (!column) return
    const draft = draftOverride ?? editing.draft
    let value: CellValue
    try {
      value = parseDraft(draft, column.kind)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      return
    }
    const current = rows.find((r) => r.key === editing.key)?.values[column.id] ?? null
    // Close the editor at once: the caller shows the new value while the server checks it. If the
    // server refuses, the editor opens again with the draft and the message.
    finishing.current = true
    const edited = editing
    setEditing(null)
    setError(null)
    scroller.current?.focus()
    finishing.current = false
    if (value === current) return
    try {
      await onEdit(edited.key, column.id, value)
    } catch (e) {
      setEditing({ ...edited, draft })
      setError(e instanceof Error ? e.message : String(e))
    }
  }
  const cancel = () => {
    // Moving focus blurs the editor, which would commit. The guard stops that.
    finishing.current = true
    setEditing(null)
    setError(null)
    scroller.current?.focus()
    finishing.current = false
  }
  const startEdit = (r: number, c: number) => {
    const row = visible[r]?.original
    const column = columns[c]
    if (!row || !column || column.readOnly) return
    if (column.kind === 'bool') {
      const next = !(row.values[column.id] === true)
      void Promise.resolve(onEdit(row.key, column.id, next)).catch((e: unknown) =>
        setError(e instanceof Error ? e.message : String(e)),
      )
      return
    }
    setError(null)
    setEditing({
      key: row.key,
      column: column.id,
      draft: draftOf(row.values[column.id]),
    })
  }

  const move = (dr: number, dc: number) => {
    const r = Math.max(0, Math.min(visible.length - 1, active.r + dr))
    const c = Math.max(0, Math.min(lastColumn, active.c + dc))
    setActive({ r, c })
    virtual.scrollToIndex(r)
  }
  const onKeyDown = (event: React.KeyboardEvent) => {
    if (editing) return
    if ((event.target as HTMLElement).closest('[data-entry-row]')) return
    const keys: Record<string, [number, number]> = {
      ArrowDown: [1, 0],
      ArrowUp: [-1, 0],
      ArrowRight: [0, 1],
      ArrowLeft: [0, -1],
      PageDown: [10, 0],
      PageUp: [-10, 0],
    }
    const step = keys[event.key]
    if (step) {
      event.preventDefault()
      move(step[0], step[1])
    } else if (event.key === 'Enter' || event.key === 'F2') {
      event.preventDefault()
      startEdit(active.r, active.c)
    }
  }

  const activeId = `${label}-cell-${active.r}-${active.c}`
  return (
    <div className="flex min-h-0 flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <label className="flex items-center gap-2 text-sm">
          <span>Filter rows</span>
          <input
            className="h-8 w-56 rounded border border-neutral-300 px-2"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
        </label>
        <span className="text-sm text-neutral-600" aria-live="polite">
          {visible.length === rows.length
            ? `${rows.length} rows`
            : `${visible.length} of ${rows.length} rows`}
        </span>
        <div className="ml-auto flex gap-2">{actions}</div>
      </div>
      {error && (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      )}
      <div
        ref={scroller}
        role="grid"
        aria-label={label}
        aria-rowcount={visible.length + 1}
        aria-colcount={columns.length}
        aria-activedescendant={visible.length ? activeId : undefined}
        tabIndex={0}
        onKeyDown={onKeyDown}
        className="relative overflow-auto rounded-md border border-neutral-300 focus-visible:outline-2 focus-visible:outline-blue-600"
        style={{ height }}
      >
        <div className="sticky top-0 z-20" style={{ minWidth: 'max-content' }}>
          <div
            role="row"
            className="grid border-b border-neutral-300 bg-neutral-100 text-sm font-semibold"
            style={{ gridTemplateColumns: template, minWidth: 'max-content' }}
          >
            {table.getHeaderGroups()[0]?.headers.map((header, i) => {
              const column = columns[i]!
              const sorted = header.column.getIsSorted()
              return (
                <div
                  key={header.id}
                  role="columnheader"
                  aria-sort={
                    sorted === 'asc' ? 'ascending' : sorted === 'desc' ? 'descending' : 'none'
                  }
                  className="min-w-0 border-r border-neutral-200 last:border-r-0"
                >
                  <button
                    className="flex h-full w-full items-center gap-1 px-2 py-1.5 text-left"
                    onClick={header.column.getToggleSortingHandler()}
                  >
                    <span className="truncate">
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {column.required && <span aria-hidden> *</span>}
                    </span>
                    <span aria-hidden>{sorted === 'asc' ? '▲' : sorted === 'desc' ? '▼' : ''}</span>
                  </button>
                </div>
              )
            })}
            {onDelete && <div role="columnheader" className="px-2 py-1.5" />}
          </div>
          {renderEntry?.({ template })}
        </div>
        <div
          style={{ height: virtual.getTotalSize(), position: 'relative', minWidth: 'max-content' }}
        >
          {virtual.getVirtualItems().map((item) => {
            const row = visible[item.index]!.original
            const rowActive = item.index === active.r
            return (
              <div
                key={row.key}
                role="row"
                aria-rowindex={item.index + 2}
                data-key={row.key}
                className={cn(
                  'absolute left-0 grid w-full border-b border-neutral-200 text-sm',
                  row.key === highlightKey && 'bg-yellow-100',
                )}
                style={{
                  height: ROW_HEIGHT,
                  transform: `translateY(${item.start}px)`,
                  gridTemplateColumns: template,
                  minWidth: 'max-content',
                }}
              >
                {columns.map((column, c) => {
                  const isEditing = editing?.key === row.key && editing.column === column.id
                  const selected = rowActive && active.c === c
                  return (
                    <div
                      key={column.id}
                      id={`${label}-cell-${item.index}-${c}`}
                      role="gridcell"
                      aria-selected={selected}
                      aria-colindex={c + 1}
                      data-column={column.id}
                      className={cn(
                        'relative flex min-w-0 items-center border-r border-neutral-100 px-2',
                        selected && 'outline-2 -outline-offset-2 outline-blue-600',
                        column.readOnly && 'bg-neutral-50 text-neutral-600',
                      )}
                      onClick={() => setActive({ r: item.index, c })}
                      onDoubleClick={() => startEdit(item.index, c)}
                    >
                      {isEditing ? (
                        <>
                          {POPOVER_KINDS.includes(column.kind) && (
                            <span className="truncate">{editing.draft}</span>
                          )}
                          <EditorFor
                            column={column}
                            label={`${column.header} of ${row.key}`}
                            value={editing.draft}
                            autoFocus
                            onChange={(draft) => setEditing({ ...editing, draft })}
                            onCommit={() => void commit()}
                            onCancel={cancel}
                          />
                        </>
                      ) : (
                        <span
                          className="truncate"
                          title={display(row.values[column.id], column.kind)}
                        >
                          {display(row.values[column.id], column.kind)}
                        </span>
                      )}
                    </div>
                  )
                })}
                {onDelete && (
                  <div role="gridcell" className="flex items-center px-1">
                    <Button
                      size="sm"
                      variant="danger"
                      aria-label={`Delete row ${row.key}`}
                      onClick={() => {
                        if (window.confirm(`Delete "${row.key}"?`)) void onDelete(row.key)
                      }}
                    >
                      Delete
                    </Button>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
