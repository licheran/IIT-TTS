import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '@/api/client'
import { useSchema, useTimetable, useTimetableCheck, useTimetableEdits } from '@/api/hooks'
import type { SheetDef } from '@/api/types'
import { DataTable, type CellValue, type DataColumn } from '@/components/DataTable'
import { ErrorList } from '@/components/ErrorList'
import { Button } from '@/components/ui/button'
import { useRefOptions } from '@/features/tables/useRefOptions'
import { editOf, sessionRows } from './rows'

// The academic resource types the session rows are made of.
const GROUPS = 'StudentGroup'
const TEACHERS = 'Teacher'
const ROOMS = 'Room'

const sheetOf = (sheets: SheetDef[], pick: (s: SheetDef) => boolean) =>
  sheets.find(pick)?.name ?? ''

/** The Activities table of a configured dataset: the solver's sessions, with the user's edits. */
export function SessionsPage({ datasetId }: { datasetId: number }) {
  const schema = useSchema(datasetId)
  const timetable = useTimetable(datasetId)
  const check = useTimetableCheck(datasetId)
  const { edit, undo, clear } = useTimetableEdits(datasetId)
  const [problem, setProblem] = useState<ApiError | null>(null)

  const sheets = useMemo(() => schema.data?.sheets ?? [], [schema.data?.sheets])
  const names = useMemo(
    () => ({
      groups: sheetOf(sheets, (s) => s.resource_type === GROUPS),
      teachers: sheetOf(sheets, (s) => s.resource_type === TEACHERS),
      rooms: sheetOf(sheets, (s) => s.resource_type === ROOMS),
      days: sheetOf(sheets, (s) => s.target === 'day'),
      periods: sheetOf(sheets, (s) => s.target === 'period'),
    }),
    [sheets],
  )
  const wanted = useMemo(() => Object.values(names).filter((n) => n !== ''), [names])
  const options = useRefOptions(datasetId, wanted)

  const columns = useMemo<DataColumn[]>(
    () => [
      { id: 'code', header: 'Code', kind: 'text', readOnly: true, width: 170 },
      { id: 'module', header: 'Module', kind: 'text', readOnly: true, width: 110 },
      { id: 'kind', header: 'Kind', kind: 'text', readOnly: true, width: 70 },
      {
        id: 'groups',
        header: 'Groups',
        kind: 'multiref',
        width: 200,
        options: options.get(names.groups) ?? [],
      },
      {
        id: 'teachers',
        header: 'Teachers',
        kind: 'multiref',
        width: 130,
        options: options.get(names.teachers) ?? [],
      },
      {
        id: 'rooms',
        header: 'Rooms',
        kind: 'multiref',
        width: 110,
        options: options.get(names.rooms) ?? [],
      },
      {
        id: 'day',
        header: 'Day',
        kind: 'choice',
        width: 80,
        options: options.get(names.days) ?? [],
      },
      {
        id: 'start',
        header: 'Start',
        kind: 'choice',
        width: 80,
        options: options.get(names.periods) ?? [],
      },
      { id: 'end', header: 'End', kind: 'text', readOnly: true, width: 80 },
    ],
    [options, names],
  )

  const sessions = useMemo(() => timetable.data?.rows ?? [], [timetable.data?.rows])
  const violations = useMemo(() => check.data?.violations ?? [], [check.data?.violations])
  const rows = useMemo(() => sessionRows(sessions, violations), [sessions, violations])

  if (timetable.isPending) return <p>Loading the activities…</p>
  if (timetable.isError)
    return <p role="alert">Could not load the activities: {timetable.error.message}</p>

  const edits = timetable.data.edits
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
      <p className="text-sm text-neutral-700">
        These are the sessions the solver made for the current run. Change a cell to keep that
        value: the next run is a complete rebuild that keeps every edit and solves the rest again.
      </p>
      {edits > 0 && (
        <div
          role="status"
          className="flex flex-wrap items-center gap-3 rounded-md border border-blue-300 bg-blue-50 p-3 text-sm"
        >
          <span>
            {edits} {edits === 1 ? 'edit' : 'edits'} waiting: press Rebuild.
          </span>
          <Link className="text-blue-800 underline" to={`/datasets/${datasetId}/run`}>
            Go to Run
          </Link>
          <Button
            size="sm"
            className="ml-auto"
            onClick={() => void guard(() => clear.mutateAsync())}
            disabled={clear.isPending}
          >
            Clear all edits
          </Button>
        </div>
      )}
      {violations.length > 0 && (
        <ErrorList
          title="Clashes in the timetable with your edits"
          errors={violations.map((v) => ({ message: v.message }))}
        />
      )}
      {problem && (
        <ErrorList
          title={problem.message}
          errors={problem.details.length ? problem.details : [{ message: problem.message }]}
        />
      )}
      {sessions.length === 0 ? (
        <p role="status" className="rounded-md border border-neutral-300 p-3 text-sm">
          Nothing solved yet: press Start on the Run tab.
        </p>
      ) : (
        <DataTable
          label="Activities"
          columns={columns}
          rows={rows}
          onEdit={(key, column, value: CellValue) =>
            guard(() => edit.mutateAsync({ code: key, body: editOf(column, value) }))
          }
          renderRowAction={(row) =>
            row.marks && row.marks.length > 0 ? (
              <Button
                size="sm"
                aria-label={`Undo edit of ${row.key}`}
                onClick={() => void guard(() => undo.mutateAsync(row.key))}
              >
                Undo edit
              </Button>
            ) : null
          }
        />
      )}
    </div>
  )
}
