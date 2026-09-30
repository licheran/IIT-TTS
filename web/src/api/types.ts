import type { components } from './schema'
import type { useSchema } from './hooks'

type S = components['schemas']

export type DatasetOut = S['DatasetOut']
// The response type as the client hands it out (openapi-fetch widens the tuples of the schema).
export type SchemaOut = NonNullable<ReturnType<typeof useSchema>['data']>
export type SheetDef = SchemaOut['sheets'][number]
export type ColumnDef = SheetDef['columns'][number]
export type TablePage = S['TablePage']
export type RowOut = S['RowOut']
export type ImportResult = S['ImportResult']
export type ImportProblem = S['ImportProblem']
export type PreflightOut = S['PreflightOut']
export type IssueOut = S['IssueOut']
export type RunOut = S['RunOut']
export type RunParams = S['RunParams']
export type ExpandOut = S['ExpandOut']
export type Grid = S['Grid']
export type GridCell = S['GridCell']
export type DiffOut = S['DiffOut']
export type EventChange = S['EventChange']
export type Cell = string | number | boolean | null

export const ACTIVE_STATUSES = ['queued', 'running']
export const isActive = (status: string) => ACTIVE_STATUSES.includes(status)
export const HAS_TIMETABLE = ['succeeded', 'cancelled_partial']
