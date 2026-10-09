import { useEffect, useRef, useState, type RefObject } from 'react'
import { Button } from '@/components/ui/button'
import { CellPopover } from '@/components/ui/popover'
import { useLookup } from '@/features/tables/lookup'

/** The `;`-separated lists and `key=value` pairs that the workbook format uses. */
export const splitList = (value: string): string[] =>
  value
    .split(';')
    .map((s) => s.trim())
    .filter(Boolean)
export const joinList = (items: string[]): string => items.join(';')

export const parsePairs = (value: string): [string, string][] =>
  splitList(value).map((part) => {
    const at = part.indexOf('=')
    return at < 0 ? [part, ''] : [part.slice(0, at), part.slice(at + 1)]
  })
export const formatPairs = (pairs: [string, string][]): string =>
  joinList(pairs.filter(([k]) => k.trim() !== '').map(([k, v]) => `${k.trim()}=${v}`))

export interface EditorProps {
  value: string
  onChange: (value: string) => void
  onCommit: () => void
  onCancel: () => void
  label: string
  options?: string[]
  /** A name to show beside a code of `options`, by code. */
  optionNames?: Record<string, string>
  autoFocus?: boolean
  /** Leaving the field commits it (the default). The entry row turns this off: Enter commits. */
  blurCommits?: boolean
  /** The tables whose rows help to fill this field: the field then offers the lookup drawer. */
  lookup?: { sheets: string[]; multiple: boolean }
}

const inputClass =
  'h-full w-full min-w-0 rounded border border-blue-500 bg-white px-1 text-sm outline-none'

interface FieldLookup {
  /** The field has a lookup and a drawer to show it in. */
  available: boolean
  /** The drawer is open, so leaving the field does not end the edit. */
  isOpen: boolean
  open: () => void
}

/** Opens the reference drawer for a field, and hands it the field's current text. */
function useFieldLookup(p: EditorProps, field: RefObject<HTMLElement | null>): FieldLookup {
  const lookup = useLookup()
  const value = useRef(p.value)
  const change = useRef(p.onChange)
  value.current = p.value
  change.current = p.onChange
  const sheets = p.lookup?.sheets ?? []
  return {
    available: lookup !== null && sheets.length > 0,
    isOpen: lookup?.isOpen ?? false,
    open: () =>
      lookup?.open({
        title: p.label,
        sheets,
        multiple: p.lookup?.multiple ?? false,
        value: () => value.current,
        change: (text) => change.current(text),
        refocus: () => field.current?.focus(),
      }),
  }
}

/** Ctrl+Space or Alt+Down opens the lookup of a field, as Alt+Down opens a dropdown. */
const isLookupKey = (event: React.KeyboardEvent) =>
  (event.ctrlKey && event.key === ' ') || (event.altKey && event.key === 'ArrowDown')

function keyHandler(p: Pick<EditorProps, 'onCommit' | 'onCancel'>, lookup?: FieldLookup) {
  return (event: React.KeyboardEvent) => {
    if (lookup?.available && isLookupKey(event)) {
      event.preventDefault()
      lookup.open()
    } else if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      p.onCommit()
    } else if (event.key === 'Escape') {
      if (lookup?.isOpen) return // the drawer closes first
      event.preventDefault()
      event.stopPropagation()
      p.onCancel()
    }
  }
}

/** The small "..." beside a field. It is reached by mouse or shortcut, never by Tab. */
function LookupButton({ label, lookup }: { label: string; lookup: FieldLookup }) {
  if (!lookup.available) return null
  return (
    <button
      type="button"
      tabIndex={-1}
      aria-label={`Look up ${label}`}
      title="Look up (Ctrl+Space)"
      onMouseDown={(e) => e.preventDefault()}
      onClick={lookup.open}
      className="h-full shrink-0 rounded px-1 text-sm text-neutral-700 hover:bg-neutral-200"
    >
      ⋯
    </button>
  )
}

const blurHandler = (p: EditorProps, lookup: FieldLookup) =>
  p.blurCommits === false || lookup.isOpen ? undefined : p.onCommit

export function TextEditor(p: EditorProps & { numeric?: boolean }) {
  const field = useRef<HTMLInputElement>(null)
  const lookup = useFieldLookup(p, field)
  return (
    <div className="flex h-full w-full min-w-0 items-center gap-0.5">
      <input
        ref={field}
        aria-label={p.label}
        className={inputClass}
        autoFocus={p.autoFocus}
        type={p.numeric ? 'number' : 'text'}
        value={p.value}
        onChange={(e) => p.onChange(e.target.value)}
        onKeyDown={keyHandler(p, lookup)}
        onBlur={blurHandler(p, lookup)}
      />
      <LookupButton label={p.label} lookup={lookup} />
    </div>
  )
}

export function ChoiceEditor(p: EditorProps) {
  return (
    <select
      aria-label={p.label}
      className={inputClass}
      autoFocus={p.autoFocus}
      value={p.value}
      onChange={(e) => p.onChange(e.target.value)}
      onKeyDown={keyHandler(p)}
      onBlur={p.blurCommits === false ? undefined : p.onCommit}
    >
      <option value="" />
      {(p.options ?? []).map((o) => (
        <option key={o} value={o}>
          {o}
        </option>
      ))}
    </select>
  )
}

/** A single reference: type to search the codes of the target sheet. */
export function RefSelect(p: EditorProps) {
  const id = useRef(`refs-${Math.random().toString(36).slice(2)}`).current
  const field = useRef<HTMLInputElement>(null)
  const lookup = useFieldLookup(p, field)
  return (
    <div className="flex h-full w-full min-w-0 items-center gap-0.5">
      <input
        ref={field}
        aria-label={p.label}
        className={inputClass}
        autoFocus={p.autoFocus}
        list={id}
        value={p.value}
        onChange={(e) => p.onChange(e.target.value)}
        onKeyDown={keyHandler(p, lookup)}
        onBlur={blurHandler(p, lookup)}
      />
      <LookupButton label={p.label} lookup={lookup} />
      <datalist id={id}>
        {(p.options ?? []).map((o) => (
          <option key={o} value={o} label={p.optionNames?.[o]} />
        ))}
      </datalist>
    </div>
  )
}

/** Several references: a filterable checklist of the target sheet's codes. */
export function MultiRefSelect(p: EditorProps) {
  const [filter, setFilter] = useState('')
  const filterField = useRef<HTMLInputElement>(null)
  const lookup = useFieldLookup(p, filterField)
  const selected = splitList(p.value)
  const shown = (p.options ?? []).filter((o) => o.toLowerCase().includes(filter.toLowerCase()))
  const toggle = (code: string) =>
    p.onChange(
      joinList(selected.includes(code) ? selected.filter((s) => s !== code) : [...selected, code]),
    )
  return (
    <CellPopover
      label={p.label}
      onKeyDown={keyHandler({ ...p, onCommit: () => undefined }, lookup)}
    >
      <div className="mb-2 flex items-center gap-1">
        <input
          ref={filterField}
          aria-label={`Filter ${p.label}`}
          className="h-control-sm min-w-0 flex-1 rounded border border-neutral-300 px-2"
          autoFocus={p.autoFocus}
          placeholder="Filter…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
        {lookup.available && (
          <Button size="sm" aria-label={`Look up ${p.label}`} onClick={lookup.open}>
            Look up
          </Button>
        )}
      </div>
      <p className="mb-1 text-xs text-neutral-600">{selected.length} selected</p>
      <ul className="max-h-48 overflow-auto">
        {shown.slice(0, 200).map((code) => (
          <li key={code}>
            <label className="flex items-center gap-2 py-0.5">
              <input
                type="checkbox"
                checked={selected.includes(code)}
                onChange={() => toggle(code)}
              />
              {code}
              {p.optionNames?.[code] && (
                <span className="truncate text-neutral-600">{p.optionNames[code]}</span>
              )}
            </label>
          </li>
        ))}
      </ul>
      <div className="mt-2 flex justify-end gap-2">
        <Button size="sm" onClick={p.onCancel}>
          Cancel
        </Button>
        <Button size="sm" variant="primary" onClick={p.onCommit}>
          Done
        </Button>
      </div>
    </CellPopover>
  )
}

/** `key=value` pairs (tags), one row each. */
export function TagEditor(p: EditorProps) {
  const pairs = parsePairs(p.value)
  const set = (next: [string, string][]) => p.onChange(formatPairs(next))
  return (
    <CellPopover label={p.label} onKeyDown={keyHandler({ ...p, onCommit: () => undefined })}>
      {pairs.map(([k, v], i) => (
        <div key={i} className="mb-1 flex gap-1">
          <input
            aria-label={`Tag ${i + 1} key`}
            className="h-control-sm w-24 rounded border border-neutral-300 px-1"
            value={k}
            autoFocus={p.autoFocus && i === 0}
            onChange={(e) => set(pairs.map((x, j) => (j === i ? [e.target.value, v] : x)))}
          />
          <input
            aria-label={`Tag ${i + 1} value`}
            className="h-control-sm min-w-0 flex-1 rounded border border-neutral-300 px-1"
            value={v}
            onChange={(e) => set(pairs.map((x, j) => (j === i ? [k, e.target.value] : x)))}
          />
          <Button
            size="sm"
            aria-label={`Remove tag ${i + 1}`}
            onClick={() => set(pairs.filter((_, j) => j !== i))}
          >
            ×
          </Button>
        </div>
      ))}
      <Button size="sm" onClick={() => p.onChange(joinList([...splitList(p.value), 'key=']))}>
        Add tag
      </Button>
      <div className="mt-2 flex justify-end gap-2">
        <Button size="sm" onClick={p.onCancel}>
          Cancel
        </Button>
        <Button size="sm" variant="primary" onClick={p.onCommit}>
          Done
        </Button>
      </div>
    </CellPopover>
  )
}

export function jsonProblem(value: string): string | null {
  if (value.trim() === '') return null
  try {
    JSON.parse(value)
    return null
  } catch (error) {
    return error instanceof Error ? error.message : 'Not valid JSON'
  }
}

export function JsonEditor(p: EditorProps) {
  const problem = jsonProblem(p.value)
  const ref = useRef<HTMLTextAreaElement>(null)
  useEffect(() => {
    if (p.autoFocus) ref.current?.focus()
  }, [p.autoFocus])
  return (
    <CellPopover label={p.label}>
      <textarea
        ref={ref}
        aria-label={`${p.label} (JSON)`}
        className="h-28 w-full rounded border border-neutral-300 p-1 font-mono text-xs"
        value={p.value}
        onChange={(e) => p.onChange(e.target.value)}
        onKeyDown={(e) => e.key === 'Escape' && p.onCancel()}
      />
      {problem && <p className="text-xs text-red-700">{problem}</p>}
      <div className="mt-2 flex justify-end gap-2">
        <Button size="sm" onClick={p.onCancel}>
          Cancel
        </Button>
        <Button size="sm" variant="primary" disabled={problem !== null} onClick={p.onCommit}>
          Done
        </Button>
      </div>
    </CellPopover>
  )
}
