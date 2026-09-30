import type { ErrorDetail } from '@/api/client'

/** Group problems by their sheet, keeping the order in which each sheet first appears. */
export function groupBySheet<T extends { sheet?: string }>(items: T[]): [string, T[]][] {
  const groups = new Map<string, T[]>()
  for (const item of items) {
    const sheet = item.sheet ?? ''
    groups.set(sheet, [...(groups.get(sheet) ?? []), item])
  }
  return [...groups.entries()]
}

export function ErrorList({
  title,
  errors,
  onSelect,
}: {
  title?: string
  errors: ErrorDetail[]
  onSelect?: (error: ErrorDetail) => void
}) {
  if (errors.length === 0) return null
  return (
    <section
      role="alert"
      aria-label={title ?? 'Problems'}
      className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-900"
    >
      <h3 className="mb-2 font-semibold">
        {title ?? 'Problems'} ({errors.length})
      </h3>
      {groupBySheet(errors).map(([sheet, items]) => (
        <div key={sheet} className="mb-2 last:mb-0">
          {sheet && <h4 className="font-medium">{sheet}</h4>}
          <ul className="list-disc pl-5">
            {items.map((item, i) => (
              <li key={i}>
                {onSelect && item.row ? (
                  <button className="text-left underline" onClick={() => onSelect(item)}>
                    {item.text ?? item.message}
                  </button>
                ) : (
                  (item.text ?? item.message)
                )}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </section>
  )
}
