import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'

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
  autoFocus?: boolean
}

const inputClass =
  'h-full w-full min-w-0 rounded border border-blue-500 bg-white px-1 text-sm outline-none'

function keyHandler(p: Pick<EditorProps, 'onCommit' | 'onCancel'>) {
  return (event: React.KeyboardEvent) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      p.onCommit()
    } else if (event.key === 'Escape') {
      event.preventDefault()
      event.stopPropagation()
      p.onCancel()
    }
  }
}

export function TextEditor(p: EditorProps & { numeric?: boolean }) {
  return (
    <input
      aria-label={p.label}
      className={inputClass}
      autoFocus={p.autoFocus}
      type={p.numeric ? 'number' : 'text'}
      value={p.value}
      onChange={(e) => p.onChange(e.target.value)}
      onKeyDown={keyHandler(p)}
      onBlur={p.onCommit}
    />
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
      onBlur={p.onCommit}
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
  return (
    <>
      <input
        aria-label={p.label}
        className={inputClass}
        autoFocus={p.autoFocus}
        list={id}
        value={p.value}
        onChange={(e) => p.onChange(e.target.value)}
        onKeyDown={keyHandler(p)}
        onBlur={p.onCommit}
      />
      <datalist id={id}>
        {(p.options ?? []).map((o) => (
          <option key={o} value={o} />
        ))}
      </datalist>
    </>
  )
}

const panelClass =
  'absolute left-0 top-full z-30 mt-1 w-72 rounded-md border border-neutral-300 bg-white p-2 text-sm shadow-lg'

/** Several references: a filterable checklist of the target sheet's codes. */
export function MultiRefSelect(p: EditorProps) {
  const [filter, setFilter] = useState('')
  const selected = splitList(p.value)
  const shown = (p.options ?? []).filter((o) => o.toLowerCase().includes(filter.toLowerCase()))
  const toggle = (code: string) =>
    p.onChange(
      joinList(selected.includes(code) ? selected.filter((s) => s !== code) : [...selected, code]),
    )
  return (
    <div
      className={panelClass}
      role="dialog"
      aria-label={p.label}
      onKeyDown={keyHandler({ ...p, onCommit: () => undefined })}
    >
      <input
        aria-label={`Filter ${p.label}`}
        className="mb-2 h-8 w-full rounded border border-neutral-300 px-2"
        autoFocus={p.autoFocus}
        placeholder="Filter…"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
      />
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
    </div>
  )
}

/** `key=value` pairs (tags), one row each. */
export function TagEditor(p: EditorProps) {
  const pairs = parsePairs(p.value)
  const set = (next: [string, string][]) => p.onChange(formatPairs(next))
  return (
    <div
      className={panelClass}
      role="dialog"
      aria-label={p.label}
      onKeyDown={keyHandler({ ...p, onCommit: () => undefined })}
    >
      {pairs.map(([k, v], i) => (
        <div key={i} className="mb-1 flex gap-1">
          <input
            aria-label={`Tag ${i + 1} key`}
            className="h-8 w-24 rounded border border-neutral-300 px-1"
            value={k}
            autoFocus={p.autoFocus && i === 0}
            onChange={(e) => set(pairs.map((x, j) => (j === i ? [e.target.value, v] : x)))}
          />
          <input
            aria-label={`Tag ${i + 1} value`}
            className="h-8 min-w-0 flex-1 rounded border border-neutral-300 px-1"
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
    </div>
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
    <div className={panelClass} role="dialog" aria-label={p.label}>
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
    </div>
  )
}
