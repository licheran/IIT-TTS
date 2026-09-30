import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { App } from './App'
import { fakeApi } from './test/fakeApi'

test('shows the API status and the datasets page', async () => {
  fakeApi({
    'GET /health': { status: 'ok' },
    'GET /presets': ['academic_weekly'],
    'GET /datasets': [],
  })
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
  expect(await screen.findByText('API: ok')).toBeInTheDocument()
  expect(await screen.findByText('No datasets yet.')).toBeInTheDocument()
  expect(screen.getByRole('option', { name: 'academic_weekly' })).toBeInTheDocument()
})
