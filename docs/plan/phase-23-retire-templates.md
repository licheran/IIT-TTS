# Phase 23 — Retire Templates and ActivityGroups

**Goal:** the academic preset no longer has Templates, ActivityGroups, ActivityTeachers, Pins or the export-only Assignments sheet in format version 2, the UI or the database, and the documentation says so.

## Read first
- `docs/adr/0007-solver-decided-sessions.md`
- `docs/spec/03-workbook-format.md` §2 (version 1 conversion)
- `backend/src/tts/presets/academic_weekly/`, `backend/src/tts/expand/`, `web/src/features/tables/ExpandPanel.tsx`, `web/src/features/tables/TablesPage.tsx`

## Tasks
- [ ] P23.1 Remove the Templates and Expand tab and its API endpoints from the academic UI. `expand/` stays only as the version 1 converter (P21.3), and a test proves nothing else imports it.
- [ ] P23.2 Remove ActivityGroups, ActivityTeachers, Pins and Assignments from the version 2 sheet definitions and the Tables tab. Migrate stored datasets: activity groups and teachers become fixed resources of their events (as the importer does); pins become locked fields; template rows are expanded once, then dropped. Migration tests on a copy of each fixture.
- [ ] P23.3 Wiki and docs:
  - remove the pages for the retired tables and tab, or turn them into a short "Retired in format version 2" note that links to the replacement;
  - update `basics.md`, `glossary.md`, `tables/README.md`, the main `README.md` and `docs/cli.md`;
  - the drift tests pass.
- [ ] P23.4 The full check:
  - backend and web checks;
  - `docker compose up --build` with `scripts/smoke.sh`, extended to the `l6-config.xlsx` path;
  - the L6 and exams fixtures.

## Acceptance
- A version 2 academic workbook has no Templates, ActivityGroups, ActivityTeachers, Pins or Assignments sheet, and the UI has no Templates tab.
- Version 1 files, including `l6.xlsx` and `templates.xlsx`, still import, and L6 meets `expected.json`.
- The smoke test passes on both paths.
