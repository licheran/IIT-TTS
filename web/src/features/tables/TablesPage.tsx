import { NavLink, Navigate, useParams, useSearchParams } from 'react-router-dom'
import { useSchema } from '@/api/hooks'
import { SessionsPage } from '@/features/sessions/SessionsPage'
import { cn } from '@/lib/utils'
import { SheetEditor } from './SheetEditor'

/** The tab that shows a configured dataset's sessions: the solver's output, not a sheet. */
export const ACTIVITIES_TAB = 'Activities'

/** One tab per sheet of the preset, taken from the dataset's schema. */
export function TablesPage({ datasetId }: { datasetId: number }) {
  const schema = useSchema(datasetId)
  const { sheet: sheetName } = useParams()
  const [search] = useSearchParams()

  if (schema.isPending) return <p>Loading tables…</p>
  if (schema.isError) return <p role="alert">Could not load the schema: {schema.error.message}</p>

  const sheets = schema.data.sheets.filter((s) => !s.export_only && !s.hidden && !s.import_only)
  const configured = schema.data.kind === 'configured'
  const showSessions = configured && sheetName === ACTIVITIES_TAB
  const current = sheets.find((s) => s.name === sheetName)
  if (!current && !showSessions) {
    const first = sheets[0]
    return first ? <Navigate to={`/datasets/${datasetId}/tables/${first.name}`} replace /> : null
  }

  return (
    <div className="flex flex-col gap-3">
      <nav aria-label="Tables" role="tablist" className="flex flex-wrap gap-1">
        {sheets.map((s) => (
          <NavLink
            key={s.name}
            role="tab"
            to={`/datasets/${datasetId}/tables/${s.name}`}
            aria-selected={s.name === current?.name}
            className={({ isActive }) =>
              cn(
                'rounded-md border px-3 py-1 text-sm',
                isActive
                  ? 'border-blue-700 bg-blue-700 text-white'
                  : 'border-neutral-300 bg-white hover:bg-neutral-100',
              )
            }
          >
            {s.label || s.name}
          </NavLink>
        ))}
        {configured && (
          <NavLink
            role="tab"
            to={`/datasets/${datasetId}/tables/${ACTIVITIES_TAB}`}
            aria-selected={showSessions}
            className={({ isActive }) =>
              cn(
                'rounded-md border px-3 py-1 text-sm',
                isActive
                  ? 'border-blue-700 bg-blue-700 text-white'
                  : 'border-neutral-300 bg-white hover:bg-neutral-100',
              )
            }
          >
            Activities
          </NavLink>
        )}
      </nav>
      {showSessions && <SessionsPage datasetId={datasetId} />}
      {current && (
        <SheetEditor
          key={current.name}
          datasetId={datasetId}
          sheet={current}
          highlightKey={search.get('find')}
        />
      )}
    </div>
  )
}
