# Phase 7 — Web UI

**Goal:** the table-first application with a Start button.

## Read first
- `web/CLAUDE.md`
- `docs/spec/06-architecture.md` §5, §6
- `docs/spec/03-workbook-format.md` §2 (sheets = tabs)

## Tasks
- [x] P7.1 Generated API client (`pnpm gen:api`) and a thin fetch wrapper with the standard error handling.
- [x] P7.2 Datasets page: list datasets, create one from a preset, and delete.
- [x] P7.3 Schema-driven table editor. There is one tab per sheet from `GET /datasets/{id}/schema`.
  - Editing: inline edits, add and delete rows.
  - Reference columns: `RefSelect` for single references and `MultiRefSelect` for join sheets.
  - Other: tag and JSON cell editors, filter and sort, virtualised rows.
- [x] P7.4 Import/export panel: upload `.xlsx` or `.zip`, show row-level errors grouped by sheet, and download the configuration.
- [x] P7.5 Pre-flight panel: issues with links that jump to the offending sheet and row.
- [x] P7.6 Start panel: `RunParams` form, Start, live progress (best score, bound, elapsed time) and Cancel.
- [x] P7.7 Result grids: pick a resource type and a resource, and show the week as a grid.
  - Each multi-period event is one cell. A joint event lists every fixed resource it serves.
  - Clicking a cell shows the event details, with pin and unpin.
- [x] P7.8 Runs list: status, score, publish, diff between two runs, re-run.
- [x] P7.9 Playwright end-to-end test: import L6, edit a room's capacity, run pre-flight, press Start, wait, open the `L6 SE / G1` grid, export the HTML.
- [x] P7.10 A performance check: the table editor with 5,000 rows scrolls and edits without visible lag (NFR-8). Record the method and result in STATUS.

## Acceptance
- `pnpm lint && pnpm typecheck && pnpm test && pnpm e2e` passes.
