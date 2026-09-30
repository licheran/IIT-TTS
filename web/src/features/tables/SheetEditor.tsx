import { useMemo, useState } from 'react'
import { ApiError } from '@/api/client'
import { useRowMutations, useTableRows } from '@/api/hooks'
import type { Cell, SchemaOut, SheetDef } from '@/api/types'
import {
  DataTable,
  EditorFor,
  POPOVER_KINDS,
  parseDraft,
  type CellValue,
} from '@/components/DataTable'
import { ErrorList } from '@/components/ErrorList'
import { Button } from '@/components/ui/button'
import { buildColumns, referencedSheets } from './columns'
import { useRefOptions } from './useRefOptions'

interface Props {
  datasetId: number
  sheet: SheetDef
  schema: SchemaOut
  highlightKey?: string | null
}

export function SheetEditor({ datasetId, sheet, schema, highlightKey }: Props) {
  const page = useTableRows(datasetId, sheet.name)
  const mutations = useRowMutations(datasetId, sheet.name)
  const refSheets = useMemo(() => referencedSheets(sheet), [sheet])
  const options = useRefOptions(datasetId, refSheets)
  const [adding, setAdding] = useState(false)
  const [problem, setProblem] = useState<ApiError | null>(null)

  const columns = useMemo(
    () => buildColumns(page.data?.headers ?? [], sheet, options),
    [page.data?.headers, sheet, options],
  )
  const rows = useMemo(
    () =>
      (page.data?.rows ?? []).map((r) => ({
        key: r.key,
        values: r.values as Record<string, CellValue>,
      })),
    [page.data?.rows],
  )

  if (page.isPending) return <p>Loading {sheet.label || sheet.name}…</p>
  if (page.isError)
    return (
      <p role="alert">
        Could not load {sheet.name}: {page.error.message}
      </p>
    )

  const guard = async <T,>(run: () => Promise<T>): Promise<T> => {
    try {
      const result = await run()
      setProblem(null)
      return result
    } catch (error) {
      setProblem(error instanceof ApiError ? error : new ApiError(0, 'error', String(error)))
      throw error
    }
  }

  return (
    <div className="flex flex-col gap-3">
      {problem && (
        <ErrorList
          title={problem.message}
          errors={problem.details.length ? problem.details : [{ message: problem.message }]}
        />
      )}
      {adding && (
        <AddRowForm
          sheet={sheet}
          schema={schema}
          columns={columns}
          onCancel={() => setAdding(false)}
          onSubmit={async (values) => {
            await guard(() => mutations.create.mutateAsync(values))
            setAdding(false)
          }}
        />
      )}
      <DataTable
        label={sheet.label || sheet.name}
        columns={columns}
        rows={rows}
        highlightKey={highlightKey}
        actions={
          <Button variant="primary" onClick={() => setAdding(true)} disabled={adding}>
            Add row
          </Button>
        }
        onEdit={(key, column, value) =>
          guard(() => mutations.update.mutateAsync({ key, values: { [column]: value } }))
        }
        onDelete={(key) => guard(() => mutations.remove.mutateAsync(key))}
      />
    </div>
  )
}

function AddRowForm({
  sheet,
  columns,
  onSubmit,
  onCancel,
}: {
  sheet: SheetDef
  schema: SchemaOut
  columns: ReturnType<typeof buildColumns>
  onSubmit: (values: Record<string, Cell>) => Promise<unknown>
  onCancel: () => void
}) {
  const editable = columns.filter((c) => !c.readOnly && !c.id.startsWith('x_'))
  const [draft, setDraft] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(null)

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      const values: Record<string, Cell> = {}
      for (const c of editable) {
        const text = draft[c.id] ?? ''
        if (text === '' && c.kind !== 'bool') continue
        values[c.id] = parseDraft(text, c.kind)
      }
      await onSubmit(values)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  return (
    <form
      aria-label={`Add a row to ${sheet.label || sheet.name}`}
      onSubmit={submit}
      className="rounded-md border border-neutral-300 bg-neutral-50 p-3"
    >
      <div
        className="grid gap-3"
        style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(190px, 1fr))' }}
      >
        {editable.map((c) => (
          <label key={c.id} className="flex flex-col gap-1 text-sm">
            <span>
              {c.header}
              {c.required && ' *'}
            </span>
            {c.kind === 'bool' ? (
              <input
                type="checkbox"
                className="h-5 w-5"
                checked={draft[c.id] === 'true'}
                onChange={(e) => setDraft({ ...draft, [c.id]: String(e.target.checked) })}
              />
            ) : (
              <div className="h-8">
                <EditorFor
                  column={{
                    kind: POPOVER_KINDS.includes(c.kind) ? 'text' : c.kind,
                    options: c.options,
                  }}
                  label={c.header}
                  value={draft[c.id] ?? ''}
                  onChange={(value) => setDraft({ ...draft, [c.id]: value })}
                  onCommit={() => undefined}
                  onCancel={() => undefined}
                />
              </div>
            )}
          </label>
        ))}
      </div>
      {error && (
        <p role="alert" className="mt-2 text-sm text-red-700">
          {error}
        </p>
      )}
      <div className="mt-3 flex gap-2">
        <Button type="submit" variant="primary">
          Add
        </Button>
        <Button onClick={onCancel}>Cancel</Button>
      </div>
    </form>
  )
}
