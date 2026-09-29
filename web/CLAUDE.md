# web/CLAUDE.md

React 18+ · TypeScript (strict) · Vite · TanStack Table + Query · Tailwind + shadcn/ui · vitest · Playwright · pnpm.

## Rules
- The API client is **generated** from the backend OpenAPI schema (`pnpm gen:api` → `src/api/schema.ts`). Never hand-write request types.
- The table editors are driven by the preset's sheet definitions from `GET /datasets/{id}/schema`. Don't hard-code column lists per entity.
- UI labels come from the preset (for example, "Teacher" or "Room"). Components under `src/components/` stay domain-neutral.
- Server state goes in TanStack Query. Local UI state goes in component state. There is no global store unless an ADR approves one.
- Run progress is fetched by polling (`refetchInterval` while status is `queued` or `running`).
- The timetable grid (`src/features/grids/`) must render multi-period events as a single cell, and joint events must list every fixed resource they serve.
- Accessibility: every interactive table cell can be reached by keyboard, and every form field has a label.

## Checks
`pnpm lint && pnpm typecheck && pnpm test`. Run `pnpm e2e` before closing a Phase 7 task.
