# Phase 13 — Wiki: skeleton and tabs

**Goal:** a user wiki in `docs/wiki/` that explains every tab of the web app: what it is for and how to use it. It is written for timetable administrators, not developers: plain language and worked examples from the L6 fixture.

## Read first
- `docs/spec/03-workbook-format.md` §1 (general rules)
- `docs/spec/02-domain-model.md` §1 (concepts) and §6.1 (academic preset)
- `web/src/routes.tsx` and `web/src/features/*` (what each tab does)

## Page shape
Every wiki page has the same sections: **What it's for**, **How to use it** (numbered steps), **Example** (L6), **Related**. Write what the code does today. If the code and a spec disagree, fix the code or log the question in STATUS; don't paper over it.

## Tasks
- [x] P13.1 Skeleton:
  - `docs/wiki/README.md` (home: what IIT-TTS does, the workflow, a map of every page), `basics.md` (codes, `;` lists, `key=value` pairs, blanks and defaults, booleans, times, `x_` columns) and `glossary.md`.
  - `backend/tests/unit/test_wiki.py` with the link check: every relative link and image in `docs/wiki/**` resolves.
  - Link the wiki from the README's Documentation table and from the CLAUDE.md repository map.
- [x] P13.2 `tabs/datasets.md`: the home page. Covers create (name, preset), open, rename and delete.
- [x] P13.3 `tabs/tables.md` and `tabs/templates-expand.md`:
  - one tab per sheet, and the preset's labels;
  - inline editing and keyboard navigation, reference pickers, list and tag editors, JSON params;
  - the always-visible entry row (Phase 12): Tab and Shift+Tab across fields, Enter adds the row and returns to the first field, Esc clears it, and how an error on add is shown;
  - delete rows, filter and sort;
  - how row errors appear;
  - the Templates **Expand** preview, then commit.
- [x] P13.4 `tabs/import-export.md`: `.xlsx` vs CSV `.zip`, atomic import, errors grouped by sheet, export, and the round trip through Excel.
- [x] P13.5 `tabs/preflight.md`: what it checks, errors vs warnings, why errors block Start, and how a reference link jumps to its row.
- [x] P13.6 `tabs/run.md`: every Start parameter (time limit, mode, workers, stage scope, lock published), live progress, cancel, and the score breakdown.
- [x] P13.7 `tabs/timetable.md` and `tabs/runs.md`:
  - the resource type and resource pickers;
  - how to read a cell (a span means several periods; a joint activity lists all its groups);
  - pin and unpin;
  - HTML, Excel and CSV exports: this grid, all of this type, and every timetable in one HTML file with a contents list (Phase 12);
  - the runs list: status, score, publish, compare two runs, re-run.
- [x] P13.8 Screenshots: `web/e2e/wiki-shots.spec.ts` (script `pnpm wiki:shots`, left out of the default `pnpm e2e`) imports L6, runs a solve and saves one PNG per tab to `docs/wiki/img/`. The tab pages embed them.
- [x] P13.9 The tab check in `test_wiki.py`: each label in `TABS` of `web/src/routes.tsx` has a page in `docs/wiki/tabs/`.

## Acceptance
- Every tab has a page with the standard shape and a screenshot.
- The link and tab checks pass in `uv run pytest -m "not scale"`.
- A reader can go from creating a dataset to a published timetable using only the wiki.
