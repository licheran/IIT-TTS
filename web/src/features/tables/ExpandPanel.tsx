import { useState } from 'react'
import { errorMessage } from '@/api/client'
import { useExpand } from '@/api/hooks'
import type { ExpandOut } from '@/api/types'
import { Button } from '@/components/ui/button'

function CodeList({ title, codes }: { title: string; codes: string[] }) {
  if (codes.length === 0) return null
  return (
    <div>
      <h4 className="font-medium">
        {title} ({codes.length})
      </h4>
      <ul className="max-h-40 overflow-auto font-mono text-xs">
        {codes.map((c) => (
          <li key={c}>{c}</li>
        ))}
      </ul>
    </div>
  )
}

export function hasChanges(diff: ExpandOut): boolean {
  return (
    diff.added.length + diff.changed.length + diff.removed.length > 0 ||
    diff.orders_added + diff.orders_removed > 0
  )
}

/** Preview what expanding the templates would change, then commit it. */
export function ExpandPanel({ datasetId }: { datasetId: number }) {
  const expand = useExpand(datasetId)
  const [preview, setPreview] = useState<ExpandOut | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const run = async (commit: boolean) => {
    setMessage(null)
    try {
      const result = await expand.mutateAsync(commit)
      if (commit) {
        setPreview(null)
        setMessage(
          result.committed
            ? `Expanded: ${result.added.length} added, ${result.changed.length} changed, ${result.removed.length} removed.`
            : 'Nothing to change.',
        )
      } else {
        setPreview(result)
      }
    } catch (error) {
      setMessage(errorMessage(error))
    }
  }

  return (
    <section
      aria-label="Expand templates"
      className="flex flex-col gap-2 rounded-md border border-neutral-300 p-3 text-sm"
    >
      <div className="flex items-center gap-3">
        <p className="flex-1">
          Templates generate activities. Preview the change before writing it to the Activities
          table. Hand-made activities are never touched.
        </p>
        <Button onClick={() => void run(false)} disabled={expand.isPending}>
          Preview expansion
        </Button>
      </div>
      {message && <p role="status">{message}</p>}
      {preview && (
        <div role="dialog" aria-label="Expansion preview" className="flex flex-col gap-2">
          {preview.problems.length > 0 && (
            <ul role="alert" className="list-disc pl-5 text-red-800">
              {preview.problems.map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          )}
          {hasChanges(preview) ? (
            <>
              <div className="grid gap-3 sm:grid-cols-3">
                <CodeList title="Added" codes={preview.added} />
                <CodeList title="Changed" codes={preview.changed} />
                <CodeList title="Removed" codes={preview.removed} />
              </div>
              <p>
                Ordering constraints: {preview.orders_added} added, {preview.orders_removed}{' '}
                removed.
              </p>
              <div className="flex gap-2">
                <Button
                  variant="primary"
                  onClick={() => void run(true)}
                  disabled={expand.isPending}
                >
                  Commit
                </Button>
                <Button onClick={() => setPreview(null)}>Cancel</Button>
              </div>
            </>
          ) : (
            <p>The activities already match the templates.</p>
          )}
        </div>
      )}
    </section>
  )
}
