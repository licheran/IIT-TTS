import type { Grid, GridCell } from '@/api/types'
import { cn } from '@/lib/utils'
import { placement } from './layout'

interface Props {
  grid: Grid
  selected?: string | null
  onSelect?: (cell: GridCell) => void
  labelOf?: (kind: string) => string
}

/**
 * The week of one resource. Each event is one block, however many periods it covers, and a joint
 * event lists every resource it is fixed on.
 */
export function GridView({ grid, selected, onSelect, labelOf = (k) => k }: Props) {
  return (
    <div
      role="table"
      aria-label={`Week of ${grid.resource}`}
      className="grid overflow-x-auto border-l border-t border-neutral-300 text-xs"
      style={{
        gridTemplateColumns: `5.5rem repeat(${grid.days.length}, minmax(8rem, 1fr))`,
        gridAutoRows: 'minmax(2.6rem, auto)',
      }}
    >
      <div
        role="columnheader"
        className="border-b border-r border-neutral-300 bg-neutral-100"
        style={{ gridRow: 1, gridColumn: 1 }}
      />
      {grid.days.map((d, i) => (
        <div
          key={d.code}
          role="columnheader"
          className="border-b border-r border-neutral-300 bg-neutral-100 px-2 py-1 text-center font-semibold"
          style={{ gridRow: 1, gridColumn: i + 2 }}
        >
          {d.label}
        </div>
      ))}
      {grid.periods.map((p, r) => (
        <div key={p.code} className="contents">
          <div
            role="rowheader"
            className="border-b border-r border-neutral-300 bg-neutral-100 px-1 py-1 text-neutral-700"
            style={{ gridRow: r + 2, gridColumn: 1 }}
          >
            {p.start}–{p.end}
          </div>
          {grid.days.map((d, i) => (
            <div
              key={d.code}
              aria-hidden
              className={cn('border-b border-r border-neutral-200', p.is_break && 'bg-neutral-100')}
              style={{ gridRow: r + 2, gridColumn: i + 2 }}
            />
          ))}
        </div>
      ))}
      {grid.cells.map((cell) => {
        const at = placement(cell)
        return (
          <button
            key={cell.event}
            role="cell"
            aria-label={`${cell.event}, ${cell.day} ${cell.start_period}`}
            aria-pressed={selected === cell.event}
            onClick={() => onSelect?.(cell)}
            className={cn(
              'relative z-10 m-0.5 overflow-hidden rounded border p-1 text-left',
              selected === cell.event
                ? 'border-blue-800 bg-blue-200'
                : 'border-blue-400 bg-blue-100 hover:bg-blue-200',
            )}
            style={{
              gridRow: at.gridRow,
              gridColumn: at.gridColumn,
              width: `calc(${at.widthPercent}% - 4px)`,
              marginLeft: `calc(${at.leftPercent}% + 2px)`,
            }}
          >
            <b className="block truncate">{cell.reference ?? cell.event}</b>
            <span className="block truncate">
              {labelOf(cell.kind)} · {cell.event}
            </span>
            {cell.fixed.length > 0 && (
              <span className="block truncate text-neutral-700">{cell.fixed.join(', ')}</span>
            )}
            {cell.chosen.length > 0 && (
              <span className="block truncate text-neutral-700">{cell.chosen.join(', ')}</span>
            )}
          </button>
        )
      })}
    </div>
  )
}
