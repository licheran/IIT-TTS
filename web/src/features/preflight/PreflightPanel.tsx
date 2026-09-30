import { Link } from 'react-router-dom'
import { useDataset, usePlanned, usePreflight } from '@/api/hooks'
import type { IssueOut } from '@/api/types'
import { Button } from '@/components/ui/button'

/** The link to the table row that an issue's reference names. */
export function refLink(datasetId: number, ref: IssueOut['refs'][number]): string | null {
  if (!ref.sheet) return null
  return `/datasets/${datasetId}/tables/${encodeURIComponent(ref.sheet)}?find=${encodeURIComponent(ref.code)}`
}

/** What the solver will schedule: each module and kind, its groups and the number of sessions. */
export function PlannedSessions({ datasetId }: { datasetId: number }) {
  const planned = usePlanned(datasetId)
  if (planned.isPending || planned.isError) return null
  const total = planned.data.reduce((sum, p) => sum + p.sessions, 0)
  return (
    <section aria-labelledby="planned-heading" className="flex flex-col gap-2">
      <h3 id="planned-heading" className="text-base font-semibold">
        Sessions to schedule ({total})
      </h3>
      {planned.data.length === 0 ? (
        <p className="text-sm">
          Nothing to schedule: give a module some session types, and groups that take it.
        </p>
      ) : (
        <div className="max-h-80 overflow-auto rounded-md border border-neutral-300">
          <table className="w-full text-sm" aria-label="Sessions to schedule">
            <thead className="sticky top-0 bg-neutral-100">
              <tr className="text-left">
                <th className="p-1">Module</th>
                <th className="p-1">Kind</th>
                <th className="p-1 text-right">Groups</th>
                <th className="p-1 text-right">Groups per session</th>
                <th className="p-1 text-right">Blocks</th>
                <th className="p-1 text-right">Per week</th>
                <th className="p-1 text-right">Sessions</th>
              </tr>
            </thead>
            <tbody>
              {planned.data.map((p) => (
                <tr key={p.demand} className="border-t border-neutral-200">
                  <td className="p-1">{p.module ?? p.demand}</td>
                  <td className="p-1">{p.kind}</td>
                  <td className="p-1 text-right" title={p.groups.join(', ')}>
                    {p.groups.length}
                  </td>
                  <td className="p-1 text-right">{p.groups_per_session ?? 'all'}</td>
                  <td className="p-1 text-right">{p.blocks}</td>
                  <td className="p-1 text-right">{p.per_week}</td>
                  <td className="p-1 text-right">{p.sessions}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

export function PreflightPanel({ datasetId }: { datasetId: number }) {
  const preflight = usePreflight(datasetId)
  const dataset = useDataset(datasetId)
  return (
    <div className="flex max-w-4xl flex-col gap-3">
      <div className="flex items-center gap-3">
        <h2 className="text-lg font-semibold">Pre-flight checks</h2>
        <Button size="sm" onClick={() => void preflight.refetch()} disabled={preflight.isFetching}>
          {preflight.isFetching ? 'Checking…' : 'Check again'}
        </Button>
      </div>
      {dataset.data?.kind === 'configured' && <PlannedSessions datasetId={datasetId} />}
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
