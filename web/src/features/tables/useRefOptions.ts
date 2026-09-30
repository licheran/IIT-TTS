import { useQueries } from '@tanstack/react-query'
import { useMemo } from 'react'
import { api, unwrap } from '@/api/client'
import { keys } from '@/api/hooks'

/** The codes held by each referenced sheet, for the reference dropdowns. */
export function useRefOptions(datasetId: number, sheets: string[]): Map<string, string[]> {
  const results = useQueries({
    queries: sheets.map((sheet) => ({
      queryKey: keys.table(datasetId, sheet),
      queryFn: () =>
        unwrap(
          api.GET('/datasets/{dataset_id}/tables/{sheet}', {
            params: { path: { dataset_id: datasetId, sheet }, query: { size: 10000 } },
          }),
        ),
    })),
  })
  const signature = results.map((r) => r.dataUpdatedAt).join(',')
  return useMemo(() => {
    const map = new Map<string, string[]>()
    results.forEach((result, i) => {
      const rows = result.data?.rows ?? []
      map.set(
        sheets[i]!,
        rows.map((r) => String(r.values.code ?? r.key)),
      )
    })
    return map
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signature, sheets.join('|')])
}
