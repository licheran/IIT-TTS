# Phase 12 — UI: quick row entry and a full HTML export

**Goal:** typing many rows is fast, and every timetable can be downloaded as one HTML file.

## Read first
- `docs/spec/06-architecture.md` §5 (the export endpoint)
- `web/src/features/tables/SheetEditor.tsx`, `web/src/components/DataTable.tsx`, `web/src/components/editors.tsx`
- `backend/src/tts/io/export_html.py`, `backend/src/tts/io/templates/grid.html.j2`, `web/src/features/grids/ResultsPage.tsx`

## Tasks
- [x] P12.1 An always-visible entry row on every table:
  - a blank row pinned under the column headers (sticky while the table scrolls), with one input per editable column lined up under its header. It replaces the "Add row" button and form;
  - **Tab** and **Shift+Tab** move across the fields. **Enter** in any field (or on the Add button) adds the row. **Esc** clears it;
  - after a successful add, the fields are cleared and focus returns to the first field, so the next row can be typed straight away;
  - on an error, the typed values stay, the message shows under the row, and focus goes to the field named in the error;
  - a second Enter while an add is still being saved is ignored;
  - tests: vitest for visibility, Tab order, Enter-adds-and-refocuses, errors and Esc. A Playwright check adds three rows to Teachers by keyboard only. The 5,000-row performance check still passes.
- [x] P12.2 Every timetable in one HTML file:
  - the HTML export with no type or code holds every group, teacher and room timetable that has events, grouped by resource type, with a **Contents** list of links at the top and a "back to contents" link per grid. It still prints one grid per page;
  - the file is named `run-<id>-all.html`. Single-grid exports are unchanged;
  - the Timetable tab gets **Export all timetables (HTML)** and **Export all of this type (HTML)**, next to the existing buttons;
  - tests: the API export has one grid per such resource, in type order, and every contents link resolves to an anchor; a unit test that anchors are unique for codes like `L6 SE / G1`; a vitest check of the link targets; the L6 end-to-end test downloads the full export.

## Acceptance
- In Teachers, three rows can be added with the keyboard only (type, Tab, type, Enter), and focus returns to the first field after each add.
- "Export all timetables (HTML)" downloads one file whose contents list links to every group, teacher and room timetable of the run.
- `pnpm lint && pnpm typecheck && pnpm test && pnpm e2e` and the backend checks pass.
