import { useRef, useState } from 'react'
import { ApiError } from '@/api/client'
import { exportUrl, useImport } from '@/api/hooks'
import type { ImportResult } from '@/api/types'
import { ErrorList } from '@/components/ErrorList'
import { Button } from '@/components/ui/button'

export function IoPanel({ datasetId }: { datasetId: number }) {
  const upload = useImport(datasetId)
  const input = useRef<HTMLInputElement>(null)
  const [result, setResult] = useState<ImportResult | null>(null)
  const [failure, setFailure] = useState<string | null>(null)

  const send = async () => {
    const file = input.current?.files?.[0]
    if (!file) return
    setResult(null)
    setFailure(null)
    try {
      setResult(await upload.mutateAsync(file))
    } catch (error) {
      setFailure(error instanceof ApiError ? error.message : String(error))
    }
  }

  return (
    <div className="flex max-w-3xl flex-col gap-8">
      <section aria-labelledby="import-heading" className="flex flex-col gap-3">
        <h2 id="import-heading" className="text-lg font-semibold">
          Import a workbook
        </h2>
        <p className="text-sm text-neutral-700">
          Upload an <code>.xlsx</code> file or a CSV <code>.zip</code>. It replaces this dataset. If
          any row has a problem, nothing is changed and every problem is listed.
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex flex-col gap-1 text-sm">
            Workbook file
            <input ref={input} type="file" accept=".xlsx,.zip" className="text-sm" />
          </label>
          <Button variant="primary" onClick={() => void send()} disabled={upload.isPending}>
            {upload.isPending ? 'Importing…' : 'Import'}
          </Button>
        </div>
        {failure && (
          <p role="alert" className="text-sm text-red-700">
            {failure}
          </p>
        )}
        {result?.ok && (
          <p role="status" className="rounded-md border border-green-300 bg-green-50 p-3 text-sm">
            Imported.{' '}
            {Object.entries(result.summary)
              .map(([sheet, n]) => `${sheet}: ${n}`)
              .join(' · ')}
          </p>
        )}
        {result && !result.ok && <ErrorList title="Nothing was imported" errors={result.errors} />}
      </section>

      <section aria-labelledby="export-heading" className="flex flex-col gap-3">
        <h2 id="export-heading" className="text-lg font-semibold">
          Download the configuration
        </h2>
        <div className="flex gap-3">
          <a
            className="inline-flex h-9 items-center rounded-md border border-neutral-300 px-3 text-sm hover:bg-neutral-100"
            href={exportUrl(datasetId, 'xlsx')}
            download
          >
            Excel (.xlsx)
          </a>
          <a
            className="inline-flex h-9 items-center rounded-md border border-neutral-300 px-3 text-sm hover:bg-neutral-100"
            href={exportUrl(datasetId, 'csvzip')}
            download
          >
            CSV files (.zip)
          </a>
        </div>
      </section>
    </div>
  )
}
