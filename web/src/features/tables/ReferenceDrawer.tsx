import { useVirtualizer } from '@tanstack/react-virtual'
import { useMemo, useRef, useState } from 'react'
import { useTableRows } from '@/api/hooks'
import { Drawer } from '@/components/ui/drawer'
import { Input } from '@/components/ui/field'
import { cn } from '@/lib/utils'
import { chosen, isChosen, type LookupRequest } from './lookup'

const ROW = 34

/**
 * The rows of the table a field refers to, read-only, so the user can tell which row they mean
 * before they type its code. A click on a row puts its code in the field. In a list field it adds
 * or removes the code and the drawer stays open; in a single field it closes.
 */
export function ReferenceDrawer({
  datasetId,
  request,
  onClose,
}: {
  datasetId: number
  request: LookupRequest
  onClose: () => void
}) {
  const [sheet, setSheet] = useState(request.sheets[0]!)
  const [search, setSearch] = useState('')
  const [, redraw] = useState(0)
  const table = useTableRows(datasetId, sheet)
  const headers = table.data?.headers ?? []
  const wanted = search.trim().toLowerCase()
  const rows = useMemo(
    () =>
      (table.data?.rows ?? []).filter(
        (r) =>
          wanted === '' ||
          r.key.toLowerCase().includes(wanted) ||
          Object.values(r.values).some((v) =>
            String(v ?? '')
              .toLowerCase()
              .includes(wanted),
          ),
      ),
    [table.data?.rows, wanted],
  )
  const scroller = useRef<HTMLDivElement>(null)
  const virtual = useVirtualizer({
    count: rows.length,
    getScrollElement: () => scroller.current,
    estimateSize: () => ROW,
    overscan: 8,
    initialRect: { width: 480, height: 640 },
  })
  const columns = `repeat(${Math.max(headers.length, 1)}, minmax(7rem, 1fr))`

  const pick = (key: string, values: Record<string, unknown>) => {
    const code = String(values.code ?? key)
    request.change(chosen(request.value(), code, request.multiple))
    if (request.multiple) redraw((n) => n + 1)
    else onClose()
  }

  return (
    <Drawer title={request.title} onClose={onClose}>
      {request.sheets.length > 1 && (
        <div role="tablist" aria-label="Table" className="flex flex-wrap gap-1 px-3 pt-3">
          {request.sheets.map((name) => (
            <button
              key={name}
              role="tab"
              type="button"
              aria-selected={name === sheet}
              onClick={() => setSheet(name)}
              className={cn(
                'h-control-sm rounded-control border px-2 text-sm',
                name === sheet
                  ? 'border-blue-700 bg-blue-700 text-white'
                  : 'border-neutral-300 bg-white hover:bg-neutral-100',
              )}
            >
              {name}
            </button>
          ))}
        </div>
      )}
      <div className="flex items-center gap-2 p-3">
        <Input
          size="sm"
          className="min-w-0 flex-1"
          aria-label="Search the table"
          placeholder="Search…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <span className="text-sm text-neutral-600" aria-live="polite">
          {rows.length} {rows.length === 1 ? 'row' : 'rows'}
        </span>
      </div>
      {table.isPending && <p className="px-3 text-sm">Loading…</p>}
      {table.isError && (
        <p role="alert" className="px-3 text-sm text-red-700">
          Could not load {sheet}.
        </p>
      )}
      {table.data && (
        <div ref={scroller} className="min-h-0 flex-1 overflow-auto border-t border-neutral-200">
          <div
            role="grid"
            aria-label={`Rows of ${sheet}`}
            className="relative min-w-max"
            style={{ height: virtual.getTotalSize() + ROW }}
          >
            <div
              role="row"
              className="sticky top-0 z-10 grid border-b border-neutral-300 bg-neutral-100 text-sm font-medium"
              style={{ gridTemplateColumns: columns, height: ROW }}
            >
              {headers.map((h) => (
                <div key={h} role="columnheader" className="truncate px-2 py-1.5">
                  {h}
                </div>
              ))}
            </div>
            {virtual.getVirtualItems().map((item) => {
              const row = rows[item.index]!
              const code = String(row.values.code ?? row.key)
              const on = isChosen(request.value(), code, request.multiple)
              return (
                <button
                  key={row.key}
                  type="button"
                  role="row"
                  aria-label={`Choose ${code}`}
                  aria-selected={on}
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => pick(row.key, row.values)}
                  className={cn(
                    'absolute left-0 top-0 grid w-full border-b border-neutral-200 text-left text-sm hover:bg-blue-50',
                    on && 'bg-blue-50 font-medium',
                  )}
                  style={{
                    gridTemplateColumns: columns,
                    height: ROW,
                    transform: `translateY(${item.start + ROW}px)`,
                  }}
                >
                  {headers.map((h, i) => (
                    <span key={h} role="gridcell" className="truncate px-2 py-1.5">
                      {i === 0 && on && request.multiple ? '✓ ' : ''}
                      {String(row.values[h] ?? '')}
                    </span>
                  ))}
                </button>
              )
            })}
          </div>
        </div>
      )}
    </Drawer>
  )
}
