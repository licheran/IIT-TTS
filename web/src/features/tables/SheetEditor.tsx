import { useMemo, useState } from 'react'
import { ApiError } from '@/api/client'
import { useRowMutations, useTableRows } from '@/api/hooks'
import type { SheetDef } from '@/api/types'
import { DataTable, type CellValue } from '@/components/DataTable'
import { ErrorList } from '@/components/ErrorList'
import { buildColumns, referencedSheets } from './columns'
import { EntryRow } from './EntryRow'
import { useRefOptions } from './useRefOptions'

interface Props {
  datasetId: number
  sheet: SheetDef
  highlightKey?: string | null
}

export function SheetEditor({ datasetId, sheet, highlightKey }: Props) {
  const page = useTableRows(datasetId, sheet.name)
  const mutations = useRowMutations(datasetId, sheet.name)
  const refSheets = useMemo(() => referencedSheets(sheet), [sheet])
  const options = useRefOptions(datasetId, refSheets)
  const [problem, setProblem] = useState<ApiError | null>(null)

  const columns = useMemo(
    () => buildColumns(page.data?.headers ?? [], sheet, options),
    [page.data?.headers, sheet, options],
  )
  const rows = useMemo(
    () =>
      (page.data?.rows ?? []).map((r) => ({
        key: r.key,
        values: r.values as Record<string, CellValue>,
      })),
    [page.data?.rows],
  )

  if (page.isPending) return <p>Loading {sheet.label || sheet.name}…</p>
  if (page.isError)
    return (
      <p role="alert">
        Could not load {sheet.name}: {page.error.message}
      </p>
    )

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
      {problem && (
        <ErrorList
          title={problem.message}
          errors={problem.details.length ? problem.details : [{ message: problem.message }]}
        />
      )}
      <DataTable
        label={sheet.label || sheet.name}
        columns={columns}
        rows={rows}
        highlightKey={highlightKey}
        renderEntry={({ template }) => (
          <EntryRow
            key={sheet.name}
            label={sheet.label || sheet.name}
            columns={columns}
            template={template}
            hasActions
            onSubmit={(values) => guard(() => mutations.create.mutateAsync(values))}
          />
        )}
        onEdit={(key, column, value) =>
          guard(() => mutations.update.mutateAsync({ key, values: { [column]: value } }))
        }
        onDelete={(key) => guard(() => mutations.remove.mutateAsync(key))}
      />
    </div>
  )
}
