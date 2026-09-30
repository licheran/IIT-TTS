import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api, unwrap } from '@/api/client'
import { AppRoutes } from './routes'

export function App() {
  const health = useQuery({
    queryKey: ['health'],
    queryFn: () => unwrap(api.GET('/health')),
    retry: false,
    refetchInterval: 15000,
  })
  const status = health.isPending ? '…' : health.isError ? 'unreachable' : health.data?.status
  return (
    <div className="mx-auto flex min-h-screen max-w-[1400px] flex-col gap-4 p-4">
      <header className="flex items-center gap-4 border-b border-neutral-300 pb-3">
        <Link to="/" className="text-xl font-bold">
          IIT-TTS
        </Link>
        <span className="text-sm text-neutral-600">IIT TimeTabling Solution</span>
        <p role="status" className="ml-auto text-sm">
          API: {status}
        </p>
      </header>
      <main className="flex-1">
        <AppRoutes />
      </main>
    </div>
  )
}
