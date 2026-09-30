# Phase 22 — Editing sessions: edits and a complete rebuild

**Goal:** the Activities table of a configured dataset shows the timetable the solver made, one row per session. The user can edit a session. The next run rebuilds the whole timetable from scratch and keeps the edited values.

## Read first
- `docs/adr/0007-solver-decided-sessions.md` (Edits are inputs to a complete rebuild)
- `docs/spec/05-solver.md` §2 (Demands) and §4.2 (pins)
- `web/src/features/tables/`, `web/src/features/grids/`, `web/src/features/runs/`, `backend/src/tts/api/routers/`

## Tasks
- [x] P22.1 The Activities table of a configured dataset:
  - one row per session of the dataset's current run (the published run, or the latest successful one): `code`, `module`, `kind`, `groups`, `teachers`, `rooms`, `day`, `start`, `end`;
  - an edit mark on each edited field;
  - no entry row: sessions come from the configuration. Before the first run the table says "Nothing solved yet: press Start".

  The API returns it as one list.
- [x] P22.2 Editing a session:
  - an edit saves a declared event of the row's demand. The row's groups become its block's fixed participants (any edit keeps them together), and the edited fields become fixed teachers or pins. An edited day or start is a pin on the time, an edited room is a pin on the room. Unedited fields stay free;
  - the row keeps showing the run's values with the edits applied, and a banner says "N edits waiting: press Rebuild";
  - **Undo edit** on a row removes its edit; **Clear all edits** removes them all.

  Tests: the API and the store for each field; vitest for the edit marks, undo and clear.
- [x] P22.3 Edits are checked straight away:
  - after each edit, the verifier checks the current run's timetable with the edits applied, in a draft copy, so the stored run is never changed;
  - clashes show on the row and on the Timetable tab, in red, before any rebuild;
  - pre-flight also checks edits (P19.5).

  Test: an edit that double-books a room gives a violation naming the room and both sessions.
- [x] P22.4 Rebuild honours every edit:
  - pressing **Start** (labelled **Rebuild** while edits are waiting) runs a complete solve;
  - declared events of a demand fix their blocks (H6), pins hold (H5), and everything else is solved again from scratch;
  - nothing is patched in place.

  Test: edit one tutorial's day and room, then rebuild. The edited values are unchanged, other sessions may change, and the verifier finds 0 hard violations.
- [x] P22.5 Exports: the Timetable tab's HTML, Excel and CSV exports show the edited timetable with no edit marks (they are outputs). The configuration workbook holds no sessions and no edits (spec 03, version 2). Test: an exported workbook of a configured dataset with edits imports to a dataset with the same configuration and no edits.
- [x] P22.6 Wiki:
  - the Activities page (the timetable, edits, undo, rebuild);
  - the Tables, Run and Import / export tab pages;
  - troubleshooting for edits that clash or no longer match;
  - updated screenshots (`pnpm wiki:shots`).

## Acceptance
- On `l6-config.xlsx`: solve, move one session to another day and room on the Activities tab, and see the clash check run straight away. Rebuild: the edited values are unchanged, and the verifier reports 0 hard violations.
- `pnpm lint && pnpm typecheck && pnpm test && pnpm e2e` and the backend checks pass. The 5,000-row check still passes.
