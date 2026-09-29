# Phase 2 — L6 fixture from the FET export

**Goal:** turn the real L6 FET export into the regression dataset.

## Read first
- `backend/tests/fixtures/l6/README.md` and `expected.json`
- `docs/spec/02-domain-model.md` §6.1
- `docs/spec/03-workbook-format.md` §2

## Tasks
- [ ] P2.1 `presets/academic_weekly/`: `types.py` (resource and reference types from spec 02 §6.1), `labels.py`, and a `sheets.py` stub (the full definitions come in Phase 3).
- [ ] P2.2 `io/fet_html.py`: `parse_fet_groups_html(path) -> FetTimetable`.
  - Each `<table id="table_…">` is one group, and its name is in `span.name`.
  - Rows have a `th.yAxis` period label. Columns are Monday to Saturday, and `<!-- span -->` comments mark cells covered by a rowspan.
  - A cell holds: an optional group list line (joint sessions), `<MODULE> <LEC|TUT>, [time text][, [ONLINE]]`, the teacher list, and an optional room.
  - `rowspan` gives the duration.
  - Deduplicate joint sessions across group tables by (day, start, module, kind, teachers, room, groups).
- [ ] P2.3 `io/fet_html.py`: `to_dataset(fet, preset="academic_weekly", assumptions=…) -> (Dataset, Result)`.
  - Structure: Level `L6`; Programmes `L6 SE` and `L6 CS`; groups under their programme; Campus `MAIN`; Building `GP`; 10 rooms, where the Auditorium gets `room_type=auditorium` and the others `room_type=lab`.
  - Time model: Periods P01–P14 (08:30–22:30), P05 (12:30) as a break, days Mon–Sat, start pattern `2H`.
  - Content: one event per session, `delivery=online` when marked `[ONLINE]`, and a `Result` holding the original placements.
- [ ] P2.4 Assumptions, recorded in `_meta.assumptions` and in the fixture README:
  - Group size 30.
  - Auditorium capacity 250.
  - Other rooms: 30 × the maximum number of groups seen in that room.
- [ ] P2.5 `tests/fixtures/l6/conftest.py`: fixtures `l6_dataset` and `l6_locked_result`. Add `test_l6_fixture.py` asserting every figure in `expected.json`.
- [ ] P2.6 A test that `verify(l6_dataset, l6_locked_result)` returns no hard violations.
- [ ] P2.7 CLI `timetabler import-fet <html> --out <xlsx>` (writes the workbook once Phase 3 exists; until then it writes JSON).

## Acceptance
- `uv run pytest tests -k l6` passes, and every number matches `expected.json`: 30 groups, 10 rooms, 57 teachers, 10 modules, 77 events (22 LEC, 55 TUT), all with duration 2, and 1 online.
- The verifier reports 0 hard violations on the original placements.

## Out of scope
Soft constraints.
