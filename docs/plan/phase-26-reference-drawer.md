# Phase 26 — Reference drawer and a consistent UI

**Goal:** when a user must type a code into a cell that refers to another table (a module, a room type, a teacher, a start pattern), they can open a **read-only reference drawer** beside the table. It shows the target table with all its columns, so the user can see which row they mean before they fill in its code. At the same time the web app gets one set of controls and sizes, so the drawer and the tables look the same everywhere.

**Proposed by the user (2026-10-09).** Scheduled last, after teacher fairness (Phase 25). A move to a component library is allowed **only if the investigation in P26.1 shows it is needed**. A full redesign of the UI is not wanted now.

## What the code looks like today (checked 2026-10-09)

- About 3,000 lines of application code. Styling is Tailwind 4 with `class-variance-authority`, `clsx` and `tailwind-merge`, and an `@/` alias: the pattern used by shadcn/ui, started but not finished.
- **One shared control:** `components/ui/button.tsx`. Every input, select, popover, banner, tab and badge is styled in place with its own Tailwind classes (28 raw `<input>`, `<select>`, `<button>` or dialog elements outside tests).
- `index.css` has ten lines and no design tokens (no shared control height, spacing, radius or text size). Control heights are already mixed: `h-7`, `h-8` and `h-9` (15 uses of `h-9`, 6 of `h-8`), which is the likely cause of "larger than needed" buttons and dropdowns.
- **References today** (`components/editors.tsx`): a native `<datalist>` for one reference, and a hand-made absolutely positioned checklist panel (`MultiRefSelect`, `TagEditor`) for several. These panels have no portal, no focus trap and no collision handling, so they can be clipped by the table's scroll area. `useRefOptions` loads only the `code` of each target row; the other columns are discarded.
- The table (`DataTable`) is headless (`@tanstack/react-table` and `@tanstack/react-virtual`). No component library would replace it.
- Tests and docs that depend on the UI: 56+ vitest cases and the e2e tests find controls by `aria-label`; the wiki screenshots (`pnpm wiki:shots`) must be redrawn after any visual change; the 5,000-row check (NFR-8, p95 16.8 ms) and the keyboard-only entry row (Phase 12) must keep passing.

## Read first
- `docs/plan/phase-12-ui-quick-entry.md` (the entry row's keyboard flow, which the drawer must not break)
- `docs/plan/phase-07-web-ui.md` (NFR-8, table-first UI)
- `web/src/components/{DataTable,editors}.tsx`, `web/src/features/tables/{EntryRow,SheetEditor,useRefOptions}.ts*`, `web/src/components/ui/button.tsx`
- `docs/wiki/tabs/Tables.md` and `docs/wiki/glossary.md`

## Options for the controls (to be decided in P26.1)

| Option | What it means | Verdict |
|---|---|---|
| A. Headless primitives with our Tailwind styles (the shadcn/ui pattern) | Add small unstyled building blocks (Radix UI, React Aria or Base UI) only for the hard parts: drawer, popover, combobox, tabs. Wrap them in our own `components/ui/*` files, as `Button` is today | **Recommended.** Continues what is already started; no visual rewrite; the table stays as it is |
| B. A full styled library (MUI, Mantine, Ant Design) | Replace every control and the look of the whole app | Not recommended: a rewrite of all screens, a second styling system next to Tailwind, and a style made for forms and dashboards, not a dense spreadsheet-like grid |
| C. No library; hand-build the drawer | Cheapest now | Repeats today's problems (focus handling, Escape, clipping, screen readers) and leaves no basis for consistency |

Versions of these libraries must be checked against React 19 and Tailwind 4 when P26.1 is done. Pin them exactly, as the other dependencies are.

## The drawer (proposal, confirmed in P26.1)

- **Where it opens:** from a reference cell, by a small button beside the field (and a keyboard shortcut, for example `Ctrl+Space` or `F1`). It is not opened by clicking the cell itself, because that starts editing.
- **What it shows:** the target sheet as a read-only table, with every filled column (for Rooms: building, capacity and type; for Groups: parent and size; for Modules: name, level and optional), a search box that filters across all columns, and the column headers sortable. It uses the same virtualised table as the main grid, so 10,000 rows stay responsive.
- **Side drawer, not a modal:** the table and the row being typed stay visible and keep their draft. At narrow widths it covers the table, with a close button.
- **Picking:** clicking (or pressing Enter on) a drawer row puts its code into the cell. For a list column (such as `Teachers.modules`) a click adds or removes the code. This is a proposal: the drawer could be reference-only, with the user typing the code themselves.
- **Columns with no `refs`** (the cells the preset parses itself: `Teachers.modules` with `module:KIND`, `Availability.resource` for any resource, selectors in Constraints): decided in P26.1 whether the drawer covers them and how.
- **Dropdowns** show `code` with the name beside it when a name exists (`HAWE — Hawe Perera`), so the context is there even without the drawer.
- It replaces `MultiRefSelect` if the drawer can do the same job; otherwise they share one list component.
- **No backend change is expected:** `GET /datasets/{id}/tables/{sheet}` already returns every column.

## Tasks
- [ ] P26.1 **Investigate, then stop and ask:**
  - run the app and list the inconsistencies in `docs/plan/phase-26-audit.md` (unplanned shifts when content loads, text that overflows its cell or panel, controls taller than the row, buttons and dropdowns of different sizes, tabs, banners). Take screenshots at 1280 px and 1024 px wide;
  - check the candidate libraries (Radix UI, React Aria, Base UI) for React 19 and Tailwind 4, and bundle size;
  - ask you to confirm: option A, B or C; the drawer's trigger; reference-only or click to pick; and what happens for the columns that have no `refs`;
  - record the decision in an ADR (`docs/adr/0008-…`, from the template) if a library is added.
- [ ] P26.2 Foundations:
  - design tokens in `index.css` (control height, row height, spacing, radius, text sizes, focus ring) and one set of control sizes;
  - shared `components/ui/` controls: `Input`, `Select`, `Badge`, `Banner`, `Tabs`, with `Button` brought in line;
  - move the existing screens to them, one screen at a time, with no change in behaviour or `aria-label`;
  - a check (a vitest or lint rule) that raw `<input>`, `<select>` and `<button>` appear only inside `components/ui/` and the table's cell editors.

  Tests: the existing vitest and e2e tests pass unchanged.
- [ ] P26.3 Overlay primitives: the drawer shell, popover and combobox, per the decision of P26.1. Focus is trapped where it should be, Escape closes the top layer only, and a panel is never clipped by the table's scroll area. `MultiRefSelect` and `TagEditor` move onto the popover.

  Tests: open and close by keyboard; Escape; focus returns to the cell.
- [ ] P26.4 The drawer:
  - `useRefOptions` keeps the full rows of the target sheets (not only the codes), loaded once and shared with the dropdowns;
  - the reference table, search, sort, and the pick action as decided;
  - the entry row's keyboard flow still works with the drawer closed, and opening and closing the drawer never loses the draft;
  - dropdowns show names beside codes.

  Tests: vitest (search, pick, list columns, the draft is kept); e2e: add a Rooms row by looking up a building in the drawer; `entry.spec.ts` unchanged; 5,000-row check still passes.
- [ ] P26.5 Fix the inconsistencies of the audit that the new controls did not already remove, and tick them off in `phase-26-audit.md`.
- [ ] P26.6 Wiki and docs: a section on the reference drawer in `docs/wiki/tabs/Tables.md` (with a picture), the Basics and glossary pages, and every screenshot redrawn with `pnpm wiki:shots`. The drift tests pass.
- [ ] P26.7 The full check: backend and web checks, `pnpm e2e`, `docker compose up --build` with `scripts/smoke.sh`, tick the boxes, log in `docs/LOG.md`, commit and push.

## Acceptance
- Every reference cell of the academic and exams presets can open the drawer and shows the target table with its columns; picking behaves as decided in P26.1.
- The keyboard-only entry-row test (`web/e2e/entry.spec.ts`) and the 5,000-row check pass unchanged.
- Raw form controls are used only inside `components/ui/` and the cell editors, and the audit has no open item.
- The wiki is up to date and its screenshots are redrawn.
- No core, solver or backend behaviour changed.
