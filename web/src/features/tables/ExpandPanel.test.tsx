import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { fakeApi } from '@/test/fakeApi'
import { ExpandPanel } from './ExpandPanel'

const preview = {
  committed: false,
  added: ['M1-LEC-01', 'M1-TUT-01'],
  changed: [],
  removed: ['M1-TUT-09'],
  orders_added: 1,
  orders_removed: 0,
  problems: [],
}

function setup() {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ExpandPanel datasetId={4} />
    </QueryClientProvider>,
  )
  return userEvent.setup()
}

test('the preview lists the changes and a commit writes them', async () => {
  const api = fakeApi({
    'POST /datasets/4/expand': ({ url }: { url: URL }) =>
      url.searchParams.get('commit') === 'true' ? { ...preview, committed: true } : preview,
  })
  const user = setup()
  await user.click(screen.getByRole('button', { name: 'Preview expansion' }))
  const dialog = await screen.findByRole('dialog', { name: 'Expansion preview' })
  expect(within(dialog).getByText('M1-LEC-01')).toBeInTheDocument()
  expect(within(dialog).getByText('Removed (1)')).toBeInTheDocument()
  await user.click(within(dialog).getByRole('button', { name: 'Commit' }))
  expect(await screen.findByRole('status')).toHaveTextContent('Expanded: 2 added')
  expect(api.calls.map((c) => c.method)).toEqual(['POST', 'POST'])
})

test('a preview with nothing to change says so', async () => {
  fakeApi({ 'POST /datasets/4/expand': { ...preview, added: [], removed: [], orders_added: 0 } })
  const user = setup()
  await user.click(screen.getByRole('button', { name: 'Preview expansion' }))
  expect(await screen.findByText('The activities already match the templates.')).toBeInTheDocument()
})
