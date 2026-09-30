import type { GridCell } from '@/api/types'

export interface Placement {
  gridRow: string
  gridColumn: number
  /** Width and left offset in percent of the day column, so overlapping events sit side by side. */
  widthPercent: number
  leftPercent: number
}

/**
 * Where a cell goes in the week grid. A multi-period event is one block spanning `span` rows.
 * Row 1 and column 1 hold the headers, so the grid starts at row 2 and column 2.
 */
export function placement(
  cell: Pick<GridCell, 'row' | 'span' | 'day_index' | 'lane' | 'lanes'>,
): Placement {
  const lanes = Math.max(1, cell.lanes)
  return {
    gridRow: `${cell.row + 2} / span ${Math.max(1, cell.span)}`,
    gridColumn: cell.day_index + 2,
    widthPercent: 100 / lanes,
    leftPercent: (100 * cell.lane) / lanes,
  }
}
