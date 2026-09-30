import { NavLink, Navigate, Outlet, Route, Routes, useParams } from 'react-router-dom'
import { useDataset } from '@/api/hooks'
import { DatasetsPage } from '@/features/datasets/DatasetsPage'
import { ResultsPage } from '@/features/grids/ResultsPage'
import { IoPanel } from '@/features/io/IoPanel'
import { PreflightPanel } from '@/features/preflight/PreflightPanel'
import { RunsPage } from '@/features/runs/RunsPage'
import { StartPanel } from '@/features/runs/StartPanel'
import { TablesPage } from '@/features/tables/TablesPage'
import { cn } from '@/lib/utils'

function useDatasetId(): number {
  return Number(useParams().id)
}

const TABS = [
  ['tables', 'Tables'],
  ['io', 'Import / export'],
  ['preflight', 'Pre-flight'],
  ['run', 'Run'],
  ['results', 'Timetable'],
  ['runs', 'Runs'],
] as const

function DatasetLayout() {
  const id = useDatasetId()
  const dataset = useDataset(id)
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold">{dataset.data?.name ?? 'Dataset'}</h1>
        {dataset.data && <p className="text-sm text-neutral-600">Preset {dataset.data.preset}</p>}
        {dataset.isError && <p role="alert">{dataset.error.message}</p>}
      </div>
      <nav aria-label="Sections" className="flex flex-wrap gap-1 border-b border-neutral-300 pb-2">
        {TABS.map(([path, label]) => (
          <NavLink
            key={path}
            to={`/datasets/${id}/${path}`}
            className={({ isActive }) =>
              cn(
                'rounded-md px-3 py-1.5 text-sm font-medium',
                isActive ? 'bg-neutral-900 text-white' : 'text-neutral-700 hover:bg-neutral-100',
              )
            }
          >
            {label}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </div>
  )
}

const withId = (Component: React.ComponentType<{ datasetId: number }>) =>
  function Wrapped() {
    return <Component datasetId={useDatasetId()} />
  }

const Tables = withId(TablesPage)
const Io = withId(IoPanel)
const Preflight = withId(PreflightPanel)
const Start = withId(StartPanel)
const Results = withId(ResultsPage)
const Runs = withId(RunsPage)

export function AppRoutes() {
  return (
    <Routes>
      <Route index element={<DatasetsPage />} />
      <Route path="datasets/:id" element={<DatasetLayout />}>
        <Route index element={<Navigate to="tables" replace />} />
        <Route path="tables/:sheet?" element={<Tables />} />
        <Route path="io" element={<Io />} />
        <Route path="preflight" element={<Preflight />} />
        <Route path="run" element={<Start />} />
        <Route path="results" element={<Results />} />
        <Route path="runs" element={<Runs />} />
      </Route>
      <Route path="*" element={<p>Page not found.</p>} />
    </Routes>
  )
}
