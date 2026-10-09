import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ApiError } from '@/api/client'
import {
  useDataset,
  usePreflight,
  useRun,
  useRunActions,
  useStartRun,
  useTimetable,
} from '@/api/hooks'
import type { RunOut, RunParams } from '@/api/types'
import { isActive } from '@/api/types'
import { ErrorList } from '@/components/ErrorList'
import { Button } from '@/components/ui/button'
import { Check, Field, Input, Select } from '@/components/ui/field'
import { Notice } from '@/components/ui/notice'

const MODES: RunParams['mode'][] = ['optimise', 'feasible', 'two_phase']

export function formatNumber(value: unknown, digits = 0): string {
  return typeof value === 'number' ? value.toFixed(digits) : '–'
}

/** The errors of a run, and the text of a crash that only the run's progress holds. */
export function whyNotFinished(run: RunOut): { message: string }[] {
  const found = run.diagnostics
    .filter((d) => d.severity === 'error')
    .map((d) => ({ message: d.message }))
  const crash = (run.progress as Record<string, unknown>).error
  return typeof crash === 'string' && crash !== '' ? [...found, { message: crash }] : found
}

export function statusText(run: RunOut): string {
  return run.status.replace('_', ' ')
}

export function StartPanel({ datasetId }: { datasetId: number }) {
  const [search, setSearch] = useSearchParams()
  const runId = search.get('run') ? Number(search.get('run')) : null
  const preflight = usePreflight(datasetId)
  const configured = useDataset(datasetId).data?.kind === 'configured'
  const edits = useTimetable(datasetId, configured).data?.edits ?? 0
  const start = useStartRun(datasetId)
  const run = useRun(runId)
  const { cancel } = useRunActions(datasetId)

  const [timeLimit, setTimeLimit] = useState('120')
  const [workers, setWorkers] = useState('')
  const [seed, setSeed] = useState('0')
  const [mode, setMode] = useState<RunParams['mode']>('optimise')
  const [lockPublished, setLockPublished] = useState(true)
  const [failure, setFailure] = useState<string | null>(null)

  const blocked = preflight.data?.has_errors ?? false
  const active = run.data ? isActive(run.data.status) : false

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setFailure(null)
    try {
      const created = await start.mutateAsync({
        time_limit_s: Number(timeLimit),
        num_workers: workers === '' ? null : Number(workers),
        seed: Number(seed),
        mode,
        lock_published: lockPublished,
      })
      setSearch({ run: String(created.run_id) })
    } catch (error) {
      setFailure(error instanceof ApiError ? error.message : String(error))
    }
  }

  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <section aria-labelledby="start-heading">
        <h2 id="start-heading" className="mb-2 text-lg font-semibold">
          Start a run
        </h2>
        {blocked && (
          <Notice tone="error" role="alert" className="mb-3">
            Pre-flight found errors, so a run cannot start.{' '}
            <Link className="underline" to={`/datasets/${datasetId}/preflight`}>
              See the problems
            </Link>
          </Notice>
        )}
        {edits > 0 && (
          <Notice role="status" className="mb-3">
            {edits} {edits === 1 ? 'edit is' : 'edits are'} waiting. A rebuild solves everything
            again and keeps {edits === 1 ? 'it' : 'them'}.{' '}
            <Link className="underline" to={`/datasets/${datasetId}/tables/Activities`}>
              See the edits
            </Link>
          </Notice>
        )}
        <form
          onSubmit={submit}
          className="grid gap-3"
          style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(170px, 1fr))' }}
        >
          <Field label="Time limit (seconds)">
            <Input
              type="number"
              min={1}
              value={timeLimit}
              onChange={(e) => setTimeLimit(e.target.value)}
            />
          </Field>
          <Field label="Workers (blank: all CPUs)">
            <Input
              type="number"
              min={1}
              value={workers}
              onChange={(e) => setWorkers(e.target.value)}
            />
          </Field>
          <Field label="Seed">
            <Input type="number" value={seed} onChange={(e) => setSeed(e.target.value)} />
          </Field>
          <Field label="Mode">
            <Select value={mode} onChange={(e) => setMode(e.target.value as RunParams['mode'])}>
              {MODES.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </Select>
          </Field>
          <Check checked={lockPublished} onChange={(e) => setLockPublished(e.target.checked)}>
            Lock published runs
          </Check>
          <div className="flex items-end">
            <Button type="submit" variant="primary" disabled={blocked || start.isPending || active}>
              {edits > 0 ? 'Rebuild' : 'Start'}
            </Button>
          </div>
        </form>
        {failure && (
          <p role="alert" className="mt-2 text-sm text-red-700">
            {failure}
          </p>
        )}
      </section>

      {run.data && (
        <section aria-labelledby="progress-heading" className="flex flex-col gap-2">
          <h2 id="progress-heading" className="text-lg font-semibold">
            Run {run.data.id}
          </h2>
          <RunProgress run={run.data} />
          {active && (
            <div>
              <Button
                variant="danger"
                onClick={() => cancel.mutate(run.data!.id)}
                disabled={run.data.cancel_requested}
              >
                {run.data.cancel_requested ? 'Cancelling…' : 'Cancel'}
              </Button>
            </div>
          )}
          {!active && (
            <div className="flex gap-3 text-sm">
              <Link
                className="text-blue-800 underline"
                to={`/datasets/${datasetId}/results?run=${run.data.id}`}
              >
                Open the timetable
              </Link>
              <Link className="text-blue-800 underline" to={`/datasets/${datasetId}/runs`}>
                All runs
              </Link>
            </div>
          )}
          <ScoreBreakdown run={run.data} />
          <ErrorList title="Why it did not finish" errors={whyNotFinished(run.data)} />
        </section>
      )}
    </div>
  )
}

export function RunProgress({ run }: { run: RunOut }) {
  const progress = run.progress as Record<string, unknown>
  return (
    <dl className="grid grid-cols-2 gap-x-6 gap-y-1 rounded-md border border-neutral-300 p-3 text-sm sm:grid-cols-4">
      <div>
        <dt className="text-neutral-600">Status</dt>
        <dd role="status" className="font-medium">
          {statusText(run)}
        </dd>
      </div>
      <div>
        <dt className="text-neutral-600">Best score</dt>
        <dd>{formatNumber(run.score ?? progress.objective)}</dd>
      </div>
      <div>
        <dt className="text-neutral-600">Bound</dt>
        <dd>{formatNumber(progress.best_bound)}</dd>
      </div>
      <div>
        <dt className="text-neutral-600">Elapsed (s)</dt>
        <dd>{formatNumber(progress.elapsed_s, 1)}</dd>
      </div>
    </dl>
  )
}

interface ScoreLine {
  penalty: number
  weight: number
  score: number
}

/** The weighted soft penalties of a run, largest first. */
export function ScoreBreakdown({ run }: { run: RunOut }) {
  const lines = Object.entries(run.score_breakdown as Record<string, ScoreLine>).sort(
    ([a, x], [b, y]) => y.score - x.score || a.localeCompare(b),
  )
  if (lines.length === 0) return null
  return (
    <table className="w-full max-w-xl text-sm" aria-label="Score breakdown">
      <thead>
        <tr className="border-b border-neutral-300 text-left">
          <th className="p-1">Constraint</th>
          <th className="p-1 text-right">Penalty</th>
          <th className="p-1 text-right">Weight</th>
          <th className="p-1 text-right">Score</th>
        </tr>
      </thead>
      <tbody>
        {lines.map(([code, line]) => (
          <tr key={code} className="border-b border-neutral-200">
            <td className="p-1">{code}</td>
            <td className="p-1 text-right">{line.penalty}</td>
            <td className="p-1 text-right">{line.weight}</td>
            <td className="p-1 text-right">{line.score}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
