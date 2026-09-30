import { useRef, useState } from 'react'
import { ApiError } from '@/api/client'
import type { Cell } from '@/api/types'
import { EditorFor, POPOVER_KINDS, parseDraft, type DataColumn } from '@/components/DataTable'
import { Button } from '@/components/ui/button'

interface Props {
  label: string
  columns: DataColumn[]
  template: string
  hasActions: boolean
  onSubmit: (values: Record<string, Cell>) => Promise<unknown>
}

const isEntryColumn = (c: DataColumn) => !c.readOnly && !c.id.startsWith('x_')

function initialDraft(columns: DataColumn[]): Record<string, string> {
  const draft: Record<string, string> = {}
  for (const c of columns) if (c.kind === 'bool') draft[c.id] = String(c.defaultValue === true)
  return draft
}

/** The column a server problem points at: its `column`, else the `[column]` in its text. */
function problemColumn(error: unknown): string | null {
  if (!(error instanceof ApiError)) return null
  const first = error.details[0]
  if (!first) return null
  return first.column ?? /\[([^\]]+)\]/.exec(first.text ?? '')?.[1] ?? null
}

/**
 * A row of inputs pinned under the table headers. Tab moves across the fields, Enter adds the
 * row and sends focus back to the first field, Escape clears the row.
 */
export function EntryRow({ label, columns, template, hasActions, onSubmit }: Props) {
  const [draft, setDraft] = useState(() => initialDraft(columns))
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const busyRef = useRef(false)
  const form = useRef<HTMLFormElement>(null)

  const focusField = (column?: string | null) => {
    const cells = Array.from(form.current?.querySelectorAll<HTMLElement>('[data-column]') ?? [])
    for (const cell of cells) {
      if (column && cell.dataset.column !== column) continue
      const field = cell.querySelector<HTMLElement>('input:not([type=checkbox]), select')
      if (field) {
        field.focus()
        return
      }
    }
  }

  // Choice and true/false values repeat from row to row, so they are kept; the rest is cleared.
  const clear = (keep: boolean) =>
    setDraft((old) => {
      const next = initialDraft(columns)
      if (keep)
        for (const c of columns)
          if ((c.kind === 'choice' || c.kind === 'bool') && old[c.id] !== undefined)
            next[c.id] = old[c.id]!
      return next
    })

  const submit = async () => {
    if (busyRef.current) return
    const values: Record<string, Cell> = {}
    let typed = false
    try {
      for (const c of columns.filter(isEntryColumn)) {
        const text = draft[c.id] ?? ''
        if (c.kind === 'bool') {
          values[c.id] = text === 'true'
          continue
        }
        if (text.trim() === '') continue
        typed = true
        values[c.id] = parseDraft(text, c.kind)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      return
    }
    if (!typed) return
    busyRef.current = true
    setBusy(true)
    setError(null)
    try {
      await onSubmit(values)
      clear(true)
      focusField()
    } catch (e) {
      // The table shows the server's message; the typed values stay for correcting.
      focusField(problemColumn(e))
    } finally {
      busyRef.current = false
      setBusy(false)
    }
  }

  return (
    <form
      ref={form}
      role="row"
      data-entry-row
      aria-label={`New row for ${label}`}
      aria-busy={busy}
      noValidate
      onSubmit={(event) => {
        event.preventDefault()
        void submit()
      }}
      onKeyDown={(event) => {
        if (event.key === 'Escape') {
          event.preventDefault()
          clear(false)
          setError(null)
          focusField()
        }
      }}
      className="grid border-b border-blue-200 bg-blue-50 text-sm"
      style={{ gridTemplateColumns: template, minWidth: 'max-content' }}
    >
      {columns.map((c) => (
        <div
          key={c.id}
          role="gridcell"
          data-column={c.id}
          className="flex min-w-0 items-center border-r border-blue-100 px-1 py-1"
        >
          {!isEntryColumn(c) ? null : c.kind === 'bool' ? (
            <input
              type="checkbox"
              aria-label={c.header}
              className="ml-1 h-5 w-5"
              checked={draft[c.id] === 'true'}
              onChange={(e) => setDraft({ ...draft, [c.id]: String(e.target.checked) })}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault()
                  void submit()
                }
              }}
            />
          ) : (
            <div className="h-8 w-full min-w-0">
              <EditorFor
                column={{
                  kind: POPOVER_KINDS.includes(c.kind) ? 'text' : c.kind,
                  options: c.options,
                }}
                label={`New ${c.header}${c.required ? ' (required)' : ''}`}
                value={draft[c.id] ?? ''}
                blurCommits={false}
                onChange={(value) => setDraft({ ...draft, [c.id]: value })}
                onCommit={() => void submit()}
                onCancel={() => {
                  clear(false)
                  setError(null)
                }}
              />
            </div>
          )}
        </div>
      ))}
      {hasActions && (
        <div role="gridcell" className="flex items-center px-1">
          <Button type="submit" size="sm" variant="primary" disabled={busy}>
            Add
          </Button>
        </div>
      )}
      {error && (
        <p role="alert" className="col-span-full px-2 pb-1 text-sm text-red-700">
          {error}
        </p>
      )}
    </form>
  )
}
