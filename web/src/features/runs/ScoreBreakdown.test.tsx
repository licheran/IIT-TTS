import { render, screen, within } from '@testing-library/react'
import type { RunOut } from '@/api/types'
import { ScoreBreakdown } from './StartPanel'

const run = (score_breakdown: RunOut['score_breakdown']) => ({ score_breakdown }) as RunOut

test('the breakdown lists each constraint, largest score first', () => {
  render(
    <ScoreBreakdown
      run={run({
        'AC-TGAPS': { penalty: 3, weight: 2, score: 6 },
        'AC-GAPS': { penalty: 4, weight: 5, score: 20 },
      })}
    />,
  )
  const rows = within(screen.getByRole('table', { name: 'Score breakdown' })).getAllByRole('row')
  expect(rows.slice(1).map((r) => r.textContent)).toEqual(['AC-GAPS4520', 'AC-TGAPS326'])
})

test('nothing is shown without soft penalties', () => {
  const { container } = render(<ScoreBreakdown run={run({})} />)
  expect(container).toBeEmptyDOMElement()
})
