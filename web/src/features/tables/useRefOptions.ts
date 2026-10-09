import { useQueries } from '@tanstack/react-query'
import { useMemo } from 'react'
import { api, unwrap } from '@/api/client'
import { keys } from '@/api/hooks'

/** The table queries of the referenced sheets (shared with the table views and the lookup). */
function useReferencedRows(datasetId: number, sheets: string[]) {
  return useQueries({
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
}

/** The codes held by each referenced sheet, for the reference dropdowns. */
export function useRefOptions(datasetId: number, sheets: string[]): Map<string, string[]> {
  const results = useReferencedRows(datasetId, sheets)
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

/** The name of each row that has one, by code, so a dropdown can show "code, name". */
export function useRefNames(datasetId: number, sheets: string[]): Map<string, string> {
  const results = useReferencedRows(datasetId, sheets)
  const signature = results.map((r) => r.dataUpdatedAt).join(',')
  return useMemo(() => {
    const names = new Map<string, string>()
    for (const result of results) {
      for (const row of result.data?.rows ?? []) {
        const name = row.values.name
        const code = String(row.values.code ?? row.key)
        if (typeof name === 'string' && name.trim() !== '' && name !== code) names.set(code, name)
      }
    }
    return names
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signature, sheets.join('|')])
}
