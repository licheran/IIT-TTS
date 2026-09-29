import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'

export function App() {
  const health = useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const { data, error } = await api.GET('/health')
      if (error) throw new Error('API unreachable')
      return data
    },
    retry: false,
  })
  const status = health.isPending ? '…' : health.isError ? 'unreachable' : health.data?.status
  return (
    <main className="p-6">
      <h1 className="text-2xl font-semibold">IIT-TTS</h1>
      <p role="status">API: {status}</p>
    </main>
  )
}
