import { useState } from 'react'
import { Link } from 'react-router-dom'
import { errorMessage } from '@/api/client'
import { useCreateDataset, useDatasets, useDeleteDataset, usePresets } from '@/api/hooks'
import { Button } from '@/components/ui/button'

export function DatasetsPage() {
  const datasets = useDatasets()
  const presets = usePresets()
  const create = useCreateDataset()
  const remove = useDeleteDataset()
  const [name, setName] = useState('')
  const [preset, setPreset] = useState('')
  const chosen = preset || presets.data?.[0] || ''

  return (
    <div className="flex flex-col gap-6">
      <section aria-labelledby="new-dataset">
        <h2 id="new-dataset" className="mb-2 text-lg font-semibold">
          New dataset
        </h2>
        <form
          className="flex flex-wrap items-end gap-3"
          onSubmit={(e) => {
            e.preventDefault()
            create.mutate({ name: name.trim(), preset: chosen }, { onSuccess: () => setName('') })
          }}
        >
          <label className="flex flex-col gap-1 text-sm">
            Name
            <input
              className="h-9 w-64 rounded border border-neutral-300 px-2"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            Preset
            <select
              className="h-9 rounded border border-neutral-300 px-2"
              value={chosen}
              onChange={(e) => setPreset(e.target.value)}
            >
              {presets.data?.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </label>
          <Button
            type="submit"
            variant="primary"
            disabled={!name.trim() || !chosen || create.isPending}
          >
            Create
          </Button>
        </form>
        {create.isError && (
          <p role="alert" className="mt-2 text-sm text-red-700">
            {errorMessage(create.error)}
          </p>
        )}
      </section>

      <section aria-labelledby="dataset-list">
        <h2 id="dataset-list" className="mb-2 text-lg font-semibold">
          Datasets
        </h2>
        {datasets.isPending && <p>Loading…</p>}
        {datasets.isError && <p role="alert">Could not load datasets: {datasets.error.message}</p>}
        {datasets.data?.length === 0 && <p className="text-neutral-600">No datasets yet.</p>}
        <ul className="divide-y divide-neutral-200 rounded-md border border-neutral-300">
          {datasets.data?.map((d) => (
            <li key={d.id} className="flex items-center gap-3 px-3 py-2">
              <Link className="font-medium text-blue-800 underline" to={`/datasets/${d.id}/tables`}>
                {d.name}
              </Link>
              <span className="text-sm text-neutral-600">
                {d.preset} · updated {new Date(d.updated_at).toLocaleString()}
              </span>
              <Button
                className="ml-auto"
                size="sm"
                variant="danger"
                aria-label={`Delete dataset ${d.name}`}
                onClick={() => {
                  if (window.confirm(`Delete dataset "${d.name}" and all its runs?`))
                    remove.mutate(d.id)
                }}
              >
                Delete
              </Button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
