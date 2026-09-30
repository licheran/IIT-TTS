# Phase 22 — Activities as the editable timetable

**Goal:** the Activities table shows the timetable the solver made, one row per session. The user can edit it. Edited fields are kept by the next run, and everything not edited is worked out again.

## Read first
- `docs/adr/0007-solver-decided-sessions.md` (Locks come from edited rows)
- `docs/spec/03-workbook-format.md` §2 (the version 2 Activities sheet), `docs/spec/05-solver.md` §4.2 (pins)
- `web/src/features/tables/`, `web/src/features/grids/`, `backend/src/tts/api/routers/`, `backend/src/tts/io/tables.py`

## Tasks
- [ ] P22.1 The Activities table in version 2:
  - one row per session of the dataset's current run (the published run, or the latest successful one): `code`, `module`, `kind`, `groups`, `teachers`, `rooms`, `day`, `start`, `end`, `locked`;
  - plus every declared event: edited and hand-made rows. `locked` lists the fields that are kept (`groups`, `teachers`, `rooms`, `day`, `start`).

  The API returns it as one list.
- [ ] P22.2 Editing a solver-made row locks it:
  - the edit saves a declared event with the row's `demand`, and its groups as fixed participants (any edit fixes the groups);
  - the edited fields become fixed teachers or pins: an edited day or start is a pin on the time, an edited room is a pin on the room;
  - unedited fields stay free;
  - the row shows a lock mark on each kept field. **Unlock** on a field frees it, and unlocking every field removes the declared event;
  - typing a new row with no demand makes a hand-made event, as today.

  Tests: the API and the store for each field; vitest for the lock marks and unlock.
- [ ] P22.3 Edits are checked straight away:
  - after each edit, the verifier checks the current run's timetable with the change applied, in a draft copy of the run, so the stored run is never changed;
  - clashes show on the row and on the Timetable tab, in red;
  - the draft is what the Timetable tab and the exports show until the next run.

  Tests: an edit that double-books a room gives a violation naming the room and both sessions.
- [ ] P22.4 The next run keeps the locks:
  - declared events of a demand count towards its cover (H6);
  - pins hold (H5);
  - everything else is recomputed.

  Test: lock one tutorial's groups and room, run again. The locked row is unchanged, the other rows may change, and the verifier finds 0 hard violations.
- [ ] P22.5 Excel round trip:
  - the version 2 export writes Activities with `locked`;
  - on import, the fields named in `locked` become declared events and pins, and the other rows are information only (they are re-solved);
  - a message explains that rows without `locked` are ignored on import.

  Round-trip test: export, lock a field in the file, import, solve, and the field is kept.
- [ ] P22.6 Wiki:
  - the Activities page (the timetable, locks, the round trip);
  - the Tables and Run tab pages;
  - troubleshooting for lock clashes;
  - updated screenshots (`pnpm wiki:shots`).

## Acceptance
- On `l6-config.xlsx`: solve; move one session to another room and lock one tutorial's groups on the Activities tab; the clash check runs straight away; run again. The locked fields are unchanged, the verifier reports 0 hard violations, and the rest may differ.
- The same through an exported and re-imported workbook.
- `pnpm lint && pnpm typecheck && pnpm test && pnpm e2e` and the backend checks pass. The 5,000-row check still passes.
