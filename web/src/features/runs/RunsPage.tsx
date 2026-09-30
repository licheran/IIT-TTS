import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useDiff, useRunActions, useRuns, useStartRun } from '@/api/hooks'
import { HAS_TIMETABLE, isActive, type RunOut } from '@/api/types'
import { Button } from '@/components/ui/button'
import { formatNumber, statusText } from './StartPanel'

export function RunsPage({ datasetId }: { datasetId: number }) {
  const runs = useRuns(datasetId)
  const { cancel, publish } = useRunActions(datasetId)
  const start = useStartRun(datasetId)
  const navigate = useNavigate()
  const [picked, setPicked] = useState<number[]>([])
  const [a, b] = picked
  const diff = useDiff(a ?? null, b ?? null)

  const toggle = (id: number) =>
    setPicked((current) =>
      current.includes(id) ? current.filter((x) => x !== id) : [...current, id].slice(-2),
    )

  const rerun = async (run: RunOut) => {
    const created = await start.mutateAsync(run.params as never)
    void navigate(`/datasets/${datasetId}/run?run=${created.run_id}`)
  }

  return (
    <div className="flex flex-col gap-6">
      <section aria-labelledby="runs-heading">
        <h2 id="runs-heading" className="mb-2 text-lg font-semibold">
          Runs
        </h2>
        {runs.data?.length === 0 && <p className="text-neutral-600">No runs yet.</p>}
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-neutral-300 text-left">
              <th className="p-2">Compare</th>
              <th className="p-2">Run</th>
              <th className="p-2">Status</th>
              <th className="p-2">Score</th>
              <th className="p-2">Started</th>
              <th className="p-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {runs.data?.map((run) => (
              <tr key={run.id} className="border-b border-neutral-200">
                <td className="p-2">
                  <input
                    type="checkbox"
                    aria-label={`Compare run ${run.id}`}
                    checked={picked.includes(run.id)}
                    disabled={!HAS_TIMETABLE.includes(run.status)}
                    onChange={() => toggle(run.id)}
                  />
                </td>
                <td className="p-2">
                  #{run.id}{' '}
                  {run.published && (
                    <span className="rounded bg-green-100 px-1 text-green-900">published</span>
                  )}
                </td>
                <td className="p-2">{statusText(run)}</td>
                <td className="p-2">{formatNumber(run.score)}</td>
                <td className="p-2">{new Date(run.created_at).toLocaleString()}</td>
                <td className="flex flex-wrap gap-2 p-2">
                  {HAS_TIMETABLE.includes(run.status) && (
                    <Link
                      className="text-blue-800 underline"
                      to={`/datasets/${datasetId}/results?run=${run.id}`}
                    >
                      Open
                    </Link>
                  )}
                  {HAS_TIMETABLE.includes(run.status) && !run.published && (
                    <Button size="sm" onClick={() => publish.mutate(run.id)}>
                      Publish
                    </Button>
                  )}
                  {isActive(run.status) && (
                    <Button size="sm" variant="danger" onClick={() => cancel.mutate(run.id)}>
                      Cancel
                    </Button>
                  )}
                  <Button size="sm" onClick={() => void rerun(run)}>
                    Re-run
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section aria-labelledby="diff-heading">
        <h2 id="diff-heading" className="mb-2 text-lg font-semibold">
          Difference between two runs
        </h2>
        {picked.length < 2 && (
          <p className="text-sm text-neutral-600">
            Tick two runs that have a timetable to compare them.
          </p>
        )}
        {diff.data && (
          <>
            <p className="mb-2 text-sm">
              Run #{diff.data.a} → run #{diff.data.b}: {diff.data.changes.length} event(s) differ.
            </p>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-neutral-300 text-left">
                  <th className="p-2">Event</th>
                  <th className="p-2">Change</th>
                  <th className="p-2">Before</th>
                  <th className="p-2">After</th>
                </tr>
              </thead>
              <tbody>
                {diff.data.changes.map((c) => (
                  <tr key={c.event} className="border-b border-neutral-200">
                    <td className="p-2">{c.event}</td>
                    <td className="p-2">{c.kind}</td>
                    <td className="p-2">
                      {c.before
                        ? `${c.before.day} ${c.before.start_period} ${c.before.resources.join(', ')}`
                        : '–'}
                    </td>
                    <td className="p-2">
                      {c.after
                        ? `${c.after.day} ${c.after.start_period} ${c.after.resources.join(', ')}`
                        : '–'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </section>
    </div>
  )
}
