import { Link } from 'react-router-dom'
import { usePreflight } from '@/api/hooks'
import type { IssueOut } from '@/api/types'
import { Button } from '@/components/ui/button'

/** The link to the table row that an issue's reference names. */
export function refLink(datasetId: number, ref: IssueOut['refs'][number]): string | null {
  if (!ref.sheet) return null
  return `/datasets/${datasetId}/tables/${encodeURIComponent(ref.sheet)}?find=${encodeURIComponent(ref.code)}`
}

export function PreflightPanel({ datasetId }: { datasetId: number }) {
  const preflight = usePreflight(datasetId)
  return (
    <div className="flex max-w-4xl flex-col gap-3">
      <div className="flex items-center gap-3">
        <h2 className="text-lg font-semibold">Pre-flight checks</h2>
        <Button size="sm" onClick={() => void preflight.refetch()} disabled={preflight.isFetching}>
          {preflight.isFetching ? 'Checking…' : 'Check again'}
        </Button>
      </div>
      {preflight.isError && <p role="alert">Could not run the checks: {preflight.error.message}</p>}
      {preflight.data?.issues.length === 0 && (
        <p role="status" className="rounded-md border border-green-300 bg-green-50 p-3 text-sm">
          No problems found. The data is ready to solve.
        </p>
      )}
      <ul className="flex flex-col gap-2">
        {preflight.data?.issues.map((issue, i) => (
          <li
            key={i}
            className={
              issue.severity === 'error'
                ? 'rounded-md border border-red-300 bg-red-50 p-3 text-sm'
                : 'rounded-md border border-amber-300 bg-amber-50 p-3 text-sm'
            }
          >
            <p>
              <strong>{issue.severity === 'error' ? 'Error' : 'Warning'}</strong> ·{' '}
              <span className="text-neutral-600">{issue.kind}</span>
            </p>
            <p>{issue.message}</p>
            <p className="mt-1 flex flex-wrap gap-2">
              {issue.refs.map((ref) => {
                const to = refLink(datasetId, ref)
                return to ? (
                  <Link key={`${ref.kind}-${ref.code}`} className="text-blue-800 underline" to={to}>
                    {ref.code} → {ref.sheet}
                  </Link>
                ) : (
                  <span key={`${ref.kind}-${ref.code}`} className="text-neutral-600">
                    {ref.code}
                  </span>
                )
              })}
            </p>
          </li>
        ))}
      </ul>
    </div>
  )
}
