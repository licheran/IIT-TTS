# Phase 23 — Retire Templates and ActivityGroups

**Goal:** the academic preset no longer has Templates, ActivityGroups, ActivityTeachers, Pins or the export-only Assignments sheet in format version 2, the UI or the database, and the documentation says so.

## Read first
- `docs/adr/0007-solver-decided-sessions.md`
- `docs/spec/03-workbook-format.md` §2 (version 1 conversion)
- `backend/src/tts/presets/academic_weekly/`, `backend/src/tts/expand/`, `web/src/features/tables/ExpandPanel.tsx`, `web/src/features/tables/TablesPage.tsx`

## Tasks
- [x] P23.1 Remove the Templates and Expand tab and its API endpoints from the academic UI. `expand/` stays only as the version 1 converter (P21.3), and a test proves nothing else imports it.
- [x] P23.2 Remove the ActivityGroups, ActivityTeachers and Pins tables from the Tables tab. A hand-made dataset shows groups and teachers as columns of Activities, and its pins as columns (`day`, `start`, `rooms`) on the same row. Migrate stored datasets: every existing dataset becomes a hand-made dataset with its events, fixed resources and pins unchanged; template rows are expanded once, then dropped. Migration tests on a copy of each fixture.
- [x] P23.3 Wiki and docs:
  - remove the pages for the retired tables and tab, or turn them into a short "Retired in format version 2" note that links to the replacement;
  - update `basics.md`, `glossary.md`, `tables/README.md`, the main `README.md` and `docs/cli.md`;
  - the drift tests pass.
- [x] P23.4 The full check:
  - backend and web checks;
  - `docker compose up --build` with `scripts/smoke.sh`, extended to the `l6-config.xlsx` path;
  - the L6 and exams fixtures.

## Acceptance
- A version 2 academic workbook has no Templates, ActivityGroups, ActivityTeachers, Pins or Assignments sheet, and the UI has no Templates tab.
- Version 1 files, including `l6.xlsx` and `templates.xlsx`, still import as hand-made datasets and export as version 1, and L6 meets `expected.json`.
- The smoke test passes on both paths.
