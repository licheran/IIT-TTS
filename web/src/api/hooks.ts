import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { API_BASE, api, unwrap } from './client'
import { isActive, type Cell, type RunParams, type TablePage } from './types'

export const keys = {
  datasets: ['datasets'] as const,
  presets: ['presets'] as const,
  schema: (id: number) => ['schema', id] as const,
  tables: (id: number) => ['table', id] as const,
  table: (id: number, sheet: string) => ['table', id, sheet] as const,
  preflight: (id: number) => ['preflight', id] as const,
  runs: (id: number) => ['runs', id] as const,
  run: (id: number) => ['run', id] as const,
  grid: (run: number, code: string) => ['grid', run, code] as const,
  diff: (a: number, b: number) => ['diff', a, b] as const,
}

export function usePresets() {
  return useQuery({
    queryKey: keys.presets,
    queryFn: () => unwrap(api.GET('/presets')),
  })
}

export function useDatasets() {
  return useQuery({
    queryKey: keys.datasets,
    queryFn: () => unwrap(api.GET('/datasets')),
  })
}

export function useCreateDataset() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (body: { name: string; preset: string }) => unwrap(api.POST('/datasets', { body })),
    onSuccess: () => client.invalidateQueries({ queryKey: keys.datasets }),
  })
}

export function useDeleteDataset() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (id: number) =>
      unwrap(api.DELETE('/datasets/{dataset_id}', { params: { path: { dataset_id: id } } })),
    onSuccess: () => client.invalidateQueries({ queryKey: keys.datasets }),
  })
}

export function useDataset(id: number) {
  return useQuery({
    queryKey: ['dataset', id],
    queryFn: () =>
      unwrap(api.GET('/datasets/{dataset_id}', { params: { path: { dataset_id: id } } })),
  })
}

export function useSchema(id: number) {
  return useQuery({
    queryKey: keys.schema(id),
    queryFn: () =>
      unwrap(api.GET('/datasets/{dataset_id}/schema', { params: { path: { dataset_id: id } } })),
    staleTime: Infinity,
  })
}

/** Every row of a sheet. Sorting, filtering and virtual scrolling happen in the browser. */
export function useTableRows(id: number, sheet: string) {
  return useQuery({
    queryKey: keys.table(id, sheet),
    queryFn: () =>
      unwrap(
        api.GET('/datasets/{dataset_id}/tables/{sheet}', {
          params: { path: { dataset_id: id, sheet }, query: { size: 10000 } },
        }),
      ),
  })
}

export function useRowMutations(id: number, sheet: string) {
  const client = useQueryClient()
  const refresh = () => {
    void client.invalidateQueries({ queryKey: keys.tables(id) })
    void client.invalidateQueries({ queryKey: keys.preflight(id) })
  }
  const path = { dataset_id: id, sheet }
  const tableKey = keys.table(id, sheet)

  /** Show a change at once. The server confirms it, or the table goes back to what it was. */
  const optimistic = async (change: (page: TablePage) => TablePage) => {
    await client.cancelQueries({ queryKey: tableKey })
    const before = client.getQueryData<TablePage>(tableKey)
    if (before) client.setQueryData<TablePage>(tableKey, change(before))
    return { before }
  }
  const rollback = (_error: unknown, _vars: unknown, context?: { before?: TablePage }) => {
    if (context?.before) client.setQueryData(tableKey, context.before)
  }

  return {
    create: useMutation({
      mutationFn: (values: Record<string, Cell>) =>
        unwrap(
          api.POST('/datasets/{dataset_id}/tables/{sheet}', {
            params: { path },
            body: { values },
          }),
        ),
      onSettled: refresh,
    }),
    update: useMutation({
      mutationFn: ({ key, values }: { key: string; values: Record<string, Cell> }) =>
        unwrap(
          api.PATCH('/datasets/{dataset_id}/tables/{sheet}/{key}', {
            params: { path: { ...path, key } },
            body: { values },
          }),
        ),
      onMutate: ({ key, values }) =>
        optimistic((page) => ({
          ...page,
          rows: page.rows.map((r) =>
            r.key === key ? { ...r, values: { ...r.values, ...values } } : r,
          ),
        })),
      onError: rollback,
      onSettled: refresh,
    }),
    remove: useMutation({
      mutationFn: (key: string) =>
        unwrap(
          api.DELETE('/datasets/{dataset_id}/tables/{sheet}/{key}', {
            params: { path: { ...path, key } },
          }),
        ),
      onMutate: (key) =>
        optimistic((page) => ({
          ...page,
          rows: page.rows.filter((r) => r.key !== key),
          total: page.total - 1,
        })),
      onError: rollback,
      onSettled: refresh,
    }),
  }
}

export function useImport(id: number) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (file: File) =>
      unwrap(
        api.POST('/datasets/{dataset_id}/import', {
          params: { path: { dataset_id: id } },
          body: { file: file as unknown as string },
          bodySerializer: () => {
            const form = new FormData()
            form.append('file', file)
            return form
          },
        }),
      ),
    onSuccess: (result) => {
      if (result.ok) {
        void client.invalidateQueries({ queryKey: keys.tables(id) })
        void client.invalidateQueries({ queryKey: keys.preflight(id) })
      }
    },
  })
}

export function exportUrl(id: number, format: 'xlsx' | 'csvzip') {
  return `${API_BASE}/datasets/${id}/export?format=${format}`
}

export function usePreflight(id: number) {
  return useQuery({
    queryKey: keys.preflight(id),
    queryFn: () =>
      unwrap(
        api.POST('/datasets/{dataset_id}/preflight', { params: { path: { dataset_id: id } } }),
      ),
  })
}

export function useRuns(id: number) {
  return useQuery({
    queryKey: keys.runs(id),
    queryFn: () =>
      unwrap(api.GET('/datasets/{dataset_id}/runs', { params: { path: { dataset_id: id } } })),
    refetchInterval: (query) => (query.state.data?.some((r) => isActive(r.status)) ? 1000 : false),
  })
}

/** A run, polled once a second while it is queued or running. */
export function useRun(runId: number | null) {
  return useQuery({
    queryKey: keys.run(runId ?? 0),
    enabled: runId !== null,
    queryFn: () => unwrap(api.GET('/runs/{run_id}', { params: { path: { run_id: runId! } } })),
    refetchInterval: (query) =>
      query.state.data && !isActive(query.state.data.status) ? false : 1000,
  })
}

export function useStartRun(id: number) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (body: RunParams) =>
      unwrap(
        api.POST('/datasets/{dataset_id}/runs', { params: { path: { dataset_id: id } }, body }),
      ),
    onSuccess: () => client.invalidateQueries({ queryKey: keys.runs(id) }),
  })
}

export function useRunActions(datasetId: number) {
  const client = useQueryClient()
  const refresh = () => {
    void client.invalidateQueries({ queryKey: keys.runs(datasetId) })
    void client.invalidateQueries({ queryKey: ['run'] })
  }
  return {
    cancel: useMutation({
      mutationFn: (runId: number) =>
        unwrap(api.POST('/runs/{run_id}/cancel', { params: { path: { run_id: runId } } })),
      onSuccess: refresh,
    }),
    publish: useMutation({
      mutationFn: (runId: number) =>
        unwrap(api.POST('/runs/{run_id}/publish', { params: { path: { run_id: runId } } })),
      onSuccess: refresh,
    }),
  }
}

export function useGrid(runId: number | null, type: string, code: string) {
  return useQuery({
    queryKey: keys.grid(runId ?? 0, `${type}/${code}`),
    enabled: runId !== null && code !== '',
    queryFn: () =>
      unwrap(
        api.GET('/runs/{run_id}/grid', {
          params: { path: { run_id: runId! }, query: { type, code } },
        }),
      ),
  })
}

export function useDiff(a: number | null, b: number | null) {
  return useQuery({
    queryKey: keys.diff(a ?? 0, b ?? 0),
    enabled: a !== null && b !== null && a !== b,
    queryFn: () => unwrap(api.GET('/runs/{a}/diff/{b}', { params: { path: { a: a!, b: b! } } })),
  })
}

export function runExportUrl(
  runId: number,
  format: 'html' | 'xlsx' | 'csv',
  type?: string,
  code?: string,
) {
  const query = new URLSearchParams({ format })
  if (type) query.set('type', type)
  if (code) query.set('code', code)
  return `${API_BASE}/runs/${runId}/export?${query.toString()}`
}
