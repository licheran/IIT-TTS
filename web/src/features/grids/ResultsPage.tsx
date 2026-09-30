import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ApiError } from '@/api/client'
import {
  runExportUrl,
  useGrid,
  useRowMutations,
  useRuns,
  useSchema,
  useTableRows,
} from '@/api/hooks'
import { HAS_TIMETABLE, type GridCell, type SchemaOut } from '@/api/types'
import { Button } from '@/components/ui/button'
import { GridView } from './GridView'

export function ResultsPage({ datasetId }: { datasetId: number }) {
  const schema = useSchema(datasetId)
  const runs = useRuns(datasetId)
  const [search, setSearch] = useSearchParams()

  const withTimetable = (runs.data ?? []).filter((r) => HAS_TIMETABLE.includes(r.status))
  const requested = search.get('run') ? Number(search.get('run')) : null
  const runId =
    requested ?? withTimetable.find((r) => r.published)?.id ?? withTimetable[0]?.id ?? null

  if (schema.isPending || runs.isPending) return <p>Loading…</p>
  if (schema.isError) return <p role="alert">Could not load the schema: {schema.error.message}</p>

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end gap-4">
        <label className="flex flex-col gap-1 text-sm">
          Run
          <select
            aria-label="Run"
            className="h-9 rounded border border-neutral-300 px-2"
            value={runId ?? ''}
            onChange={(e) => setSearch({ run: e.target.value })}
          >
            {withTimetable.length === 0 && <option value="">No timetable yet</option>}
            {withTimetable.map((r) => (
              <option key={r.id} value={r.id}>
                #{r.id} {r.status.replace('_', ' ')}
                {r.published ? ' (published)' : ''}
              </option>
            ))}
          </select>
        </label>
      </div>
      {runId === null ? (
        <p className="text-neutral-600">Start a run to see a timetable here.</p>
      ) : (
        <ResourceGrid datasetId={datasetId} runId={runId} schema={schema.data} />
      )}
    </div>
  )
}

function ResourceGrid({
  datasetId,
  runId,
  schema,
}: {
  datasetId: number
  runId: number
  schema: SchemaOut
}) {
  const sheets = useMemo(
    () => schema.sheets.filter((s) => s.resource_type != null && !s.export_only),
    [schema],
  )
  const [type, setType] = useState(
    () =>
      sheets.find((s) => s.resource_type === 'StudentGroup')?.resource_type ??
      sheets[0]?.resource_type ??
      '',
  )
  const [code, setCode] = useState('')
  const [selected, setSelected] = useState<GridCell | null>(null)
  const sheet = sheets.find((s) => s.resource_type === type)
  const label = (word: string) => schema.labels[word] ?? word

  const rows = useTableRows(datasetId, sheet?.name ?? '_meta')
  const codes = (sheet ? (rows.data?.rows ?? []) : []).map((r) => String(r.values.code ?? r.key))
  const current = code && codes.includes(code) ? code : (codes[0] ?? '')
  const grid = useGrid(runId, type, current)

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end gap-4">
        <label className="flex flex-col gap-1 text-sm">
          Resource type
          <select
            aria-label="Resource type"
            className="h-9 rounded border border-neutral-300 px-2"
            value={type ?? ''}
            onChange={(e) => {
              setType(e.target.value)
              setCode('')
              setSelected(null)
            }}
          >
            {sheets.map((s) => (
              <option key={s.name} value={s.resource_type ?? ''}>
                {label(s.resource_type ?? '')}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Resource
          <select
            aria-label="Resource"
            className="h-9 w-64 rounded border border-neutral-300 px-2"
            value={current}
            onChange={(e) => {
              setCode(e.target.value)
              setSelected(null)
            }}
          >
            {codes.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
        {current && (
          <a
            className="inline-flex h-9 items-center rounded-md border border-neutral-300 px-3 text-sm hover:bg-neutral-100"
            href={runExportUrl(runId, 'html', type ?? undefined, current)}
            download
          >
            Export this grid (HTML)
          </a>
        )}
        {type && (
          <a
            className="inline-flex h-9 items-center rounded-md border border-neutral-300 px-3 text-sm hover:bg-neutral-100"
            href={runExportUrl(runId, 'html', type)}
            download
          >
            Export all of this type (HTML)
          </a>
        )}
        <a
          className="inline-flex h-9 items-center rounded-md border border-neutral-300 px-3 text-sm hover:bg-neutral-100"
          href={runExportUrl(runId, 'html')}
          download
        >
          Export all timetables (HTML)
        </a>
        <a
          className="inline-flex h-9 items-center rounded-md border border-neutral-300 px-3 text-sm hover:bg-neutral-100"
          href={runExportUrl(runId, 'xlsx')}
          download
        >
          Export all (Excel)
        </a>
      </div>

      {grid.isError && <p role="alert">Could not load the grid: {grid.error.message}</p>}
      {grid.data && (
        <div className="grid gap-4 lg:grid-cols-[1fr_20rem]">
          <GridView
            grid={grid.data}
            selected={selected?.event}
            onSelect={setSelected}
            labelOf={label}
          />
          <EventDetails
            datasetId={datasetId}
            schema={schema}
            cell={selected}
            onClose={() => setSelected(null)}
          />
        </div>
      )}
    </div>
  )
}

function EventDetails({
  datasetId,
  schema,
  cell,
  onClose,
}: {
  datasetId: number
  schema: SchemaOut
  cell: GridCell | null
  onClose: () => void
}) {
  const pinSheet = schema.sheets.find((s) => s.target === 'pin')
  const pins = useTableRows(datasetId, pinSheet?.name ?? '_meta')
  const mutations = useRowMutations(datasetId, pinSheet?.name ?? '_meta')
  const [message, setMessage] = useState<string | null>(null)

  if (!cell) {
    return <p className="text-sm text-neutral-600">Click an event to see its details.</p>
  }
  const column = (field: string) => pinSheet?.columns.find((c) => c.field === field)?.name
  const pinned = pins.data?.rows.some((r) => r.key === cell.event) ?? false

  const pin = async () => {
    if (!pinSheet) return
    const values: Record<string, string | null> = {}
    const set = (field: string, value: string | null) => {
      const name = column(field)
      if (name) values[name] = value
    }
    set('event', cell.event)
    set('day', cell.day)
    set('start_period', cell.start_period)
    set('resources', cell.chosen.length ? cell.chosen.join(';') : null)
    try {
      await mutations.create.mutateAsync(values)
      setMessage('Pinned. Start a new run to apply it.')
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : String(error))
    }
  }
  const unpin = async () => {
    try {
      await mutations.remove.mutateAsync(cell.event)
      setMessage('Unpinned. Start a new run to apply it.')
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : String(error))
    }
  }

  return (
    <aside
      aria-label="Event details"
      className="flex flex-col gap-2 rounded-md border border-neutral-300 p-3 text-sm"
    >
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">{cell.event}</h3>
        <Button size="sm" variant="ghost" onClick={onClose} aria-label="Close details">
          ×
        </Button>
      </div>
      <dl className="grid grid-cols-[6rem_1fr] gap-y-1">
        <dt className="text-neutral-600">Kind</dt>
        <dd>{schema.labels[cell.kind] ?? cell.kind}</dd>
        {cell.reference && (
          <>
            <dt className="text-neutral-600">Reference</dt>
            <dd>{cell.reference}</dd>
          </>
        )}
        <dt className="text-neutral-600">When</dt>
        <dd>
          {cell.day} from {cell.start_period}, {cell.duration} period(s)
        </dd>
        <dt className="text-neutral-600">Serves</dt>
        <dd>{cell.fixed.join(', ') || '–'}</dd>
        <dt className="text-neutral-600">Chosen</dt>
        <dd>{cell.chosen.join(', ') || '–'}</dd>
      </dl>
      {pinSheet && (
        <div className="flex gap-2">
          {pinned ? (
            <Button onClick={() => void unpin()}>Unpin</Button>
          ) : (
            <Button variant="primary" onClick={() => void pin()}>
              Pin here
            </Button>
          )}
        </div>
      )}
      {message && <p role="status">{message}</p>}
    </aside>
  )
}
