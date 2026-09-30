import { NavLink, Navigate, useParams, useSearchParams } from 'react-router-dom'
import { useSchema } from '@/api/hooks'
import { cn } from '@/lib/utils'
import { ExpandPanel } from './ExpandPanel'
import { SheetEditor } from './SheetEditor'

/** One tab per sheet of the preset, taken from the dataset's schema. */
export function TablesPage({ datasetId }: { datasetId: number }) {
  const schema = useSchema(datasetId)
  const { sheet: sheetName } = useParams()
  const [search] = useSearchParams()

  if (schema.isPending) return <p>Loading tables…</p>
  if (schema.isError) return <p role="alert">Could not load the schema: {schema.error.message}</p>

  const sheets = schema.data.sheets.filter((s) => !s.export_only)
  const current = sheets.find((s) => s.name === sheetName)
  if (!current) {
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
            aria-selected={s.name === current.name}
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
      </nav>
      {current.target === 'template' && <ExpandPanel datasetId={datasetId} />}
      <SheetEditor
        key={current.name}
        datasetId={datasetId}
        sheet={current}
        highlightKey={search.get('find')}
      />
    </div>
  )
}
