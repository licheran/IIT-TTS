# Phase 28 — Guided data entry: hierarchy, table order, field help and better inputs

**Goal:** a timetable administrator can fill a configured dataset from the first tab to the last without guessing. The hierarchy is the one they know (University → Programme → Level → Module, groups in a level). Every table only refers to tables that come before it. Every field explains itself through an info icon. Every input shows and checks its format, and time and date fields have pickers.

**Proposed by the user (2026-10-12).** Five parts: (1) hints, validation and pickers for inputs (dates, 12 h or 24 h times, and any other input with the same problem); (2) the hierarchy University → Programme → Level → Module; (3) tabs in the order the tables can be filled (least dependent first); (4) groups have a `level`, not a `parent`; (5) an info icon that explains each field (for example what `weekly` means in Session).

**Decided by the user (2026-10-12):**
- **One level per module.** A level belongs to one programme (`CS-L6`, `SE-L6`). A module has exactly one level. A module taught to two programmes is entered twice, with two codes, so the groups of the two programmes never share a session of it. (Today `6COSC021C` and `6ELEN018C` are shared by CS and SE in the L6 configuration, and their lectures can join both programmes.)
- **A Level row has no `code` column.** The user picks the `programme` and types the `level` (for example `L6`). The code is derived as `<programme>-<level>` (`CS-L6`), as on the Session table (`SheetDef.key_from`).
- **Format version 2 is amended, not bumped** (ADR-0007 Amendment 3, as Amendments 1 and 2). No version 2 file exists outside this repository, and nothing is pushed. A database migration converts stored datasets.
- **Version 1 is left as it is** (hand-made datasets, the FET import, the L6 fixture, exams): its hierarchy and columns do not change. `backend/tests/fixtures/l6/expected.json` is not touched.

**My assumption, to confirm in P28.1:** `Programmes.university` is **required**, because "a group always has a university, a programme and a level". The L6 configuration gets one university (an assumption recorded in its `_meta`).

## Read first
- `docs/spec/03-workbook-format.md` §1, §2a, §3 (version 2 sheets, the Session amendment, validation)
- `docs/spec/02-domain-model.md` §6.1 (academic mapping: parents)
- `docs/adr/0007-solver-decided-sessions.md` (Amendments 1 and 2), `docs/plan/phase-24-session-table.md` (how `key_from` and the migration were done)
- `backend/src/tts/core/sheets.py`, `backend/src/tts/presets/academic_weekly/{sheets,types,configuration,labels}.py`, `backend/src/tts/io/{importer,tables}.py`
- `web/src/features/tables/{TablesPage,SheetEditor,EntryRow,columns}.ts*`, `web/src/components/{DataTable,editors}.tsx`, `web/src/components/ui/`
- `docs/wiki/tables/*.md` and `backend/tests/unit/test_wiki*.py` (the wiki checks)

## Today (checked 2026-10-12)

**Hierarchy (version 2).** Level → University, Programme → Level, Group → Programme (`parent`), Module has `level*` and `programmes` (a list of programmes at that level). So a level sits *above* a programme, and a group reaches its level only through its programme. In the L6 configuration the programme codes are `L6 CS` and `L6 SE`: they are really "a programme's level".

**Tab order (version 2).** Days, Periods, Start patterns, Universities, Levels, Programmes, Groups, Teachers, Campuses, Buildings, Rooms, Session types, Modules, Session, Availability, Constraints, Activities. Forward references: Groups (`options` → Modules) and Teachers (`modules` → Modules and Session) come before Modules; Session types (`room_type`, the values used on Rooms) come after Rooms only by chance. The tabs are one wrapped row with no grouping.

**Inputs.** The web app has editors for text, int, bool, choice, ref, multiref, tags and JSON. Columns of kind `time` (`Periods.start`, `Periods.end`) are plain text: nothing says `HH:MM` 24-hour until the save fails. The exams preset's `Days.code` is a date by convention but a plain text column. Other weak spots found so far (to be confirmed by the audit in P28.8):

| Column(s) | Problem today |
|---|---|
| `Periods.start`, `Periods.end` (both presets) | Free text; the format (`HH:MM`, 24-hour) is not shown; `end` after `start` is checked only on import |
| exams `Days.code` | A date by convention; no format shown, no calendar |
| `Rooms.room_type`, `SessionTypes.room_type`, `Session.room_type` | Free text that must match across tables; a typo is found only by pre-flight (`no_candidate`) |
| `Teachers.modules` | `module` or `module:KIND`; the lookup shows modules but not their session kinds |
| `Constraints.params` | Raw JSON; the parameters of each type are only in the wiki |
| `Constraints.scope` | Selector syntax with no help and no lookup (left out in P26.1) |
| int columns (`weekly`, `max_groups`, `teachers`, `max_hours`, `size`, `capacity`, `order`) | No unit or minimum shown (`max_hours` counts periods per week) |
| choice columns (`delivery`, `status`) | Codes (`in_person`) shown instead of the labels the preset has (`In person`) |
| `Availability.period` | `*` (the whole day) is allowed but not offered |
| Session cells left blank | Blank takes the session type's value, but the cell looks empty |

**Field descriptions.** `ColumnDef` has a `label` but no description. The wiki's table pages already explain each column in a "Meaning" cell, so that is where the text for the info icon comes from.

## The new version 2 tables (proposal for P28.1)

Each table only refers to tables above it.

| Section | Sheet | Columns (`*` required, `→X` reference) |
|---|---|---|
| Time | `Days` | unchanged |
| | `Periods` | unchanged |
| | `StartPatterns` | unchanged |
| Places | `Campuses` | unchanged |
| | `Buildings` | unchanged |
| | `Rooms` | unchanged |
| Academic structure | `Universities` | `code*`, `name`, `tags` (unchanged) |
| | `Programmes` | `code*`, `name`, `university*` (→Universities, the parent; was `level`), `tags` |
| | `Levels` | `programme*` (→Programmes, the parent), `level*` (text, for example `L6`), `name`, `tags`. **No `code` column:** the code is `<programme>-<level>` |
| | `Modules` | `code*`, `name`, `level*` (→Levels; exactly one), `optional` (default false), `tags`. **`programmes` is removed** |
| | `Groups` | `code*`, `name`, `level*` (→Levels, the parent; **was `parent` →Programmes**), `size`, `options` (→Modules at the group's level), `tags` |
| Teaching | `SessionTypes` | unchanged (`room_type` suggests the room types used on Rooms) |
| | `Session` | unchanged |
| | `Teachers` | unchanged (`modules`, `max_hours`) |
| Rules | `Availability` | unchanged |
| | `Constraints` | unchanged |
| Timetable | Activities (the solver's sessions, not a sheet) | unchanged |

**Who takes a module.** A mandatory module is taken by every group of its level. An optional module is taken only by the groups of its level that list it in `options`. A group that lists a module of another level is an error (as today).

## Tasks

- [ ] P28.1 **Spec and ADR (stop and ask before writing code).** Write ADR-0007 Amendment 3 (the hierarchy, one level per module, the derived Level code, `Programmes.university` required, the section order) and update spec 02 §6.1 (version 2 parents: Programme → University, Level → Programme, Group → Level), spec 03 §2a (the table above, the sheet order, "who takes a module"), §3 (new messages: duplicate `programme` + `level`, `module "X" is at level "A", the group is at level "B"`) and §1 rule 13 (sheets in section order). Show the user the diff of spec 03 §2a and the list of messages; ask whether `Programmes.university` is required. Add a `docs/LOG.md` note: format version 2 amended (rule 4).
- [ ] P28.2 **Derived codes for resource sheets.** `SheetDef.key_from` works on `target="resource"` sheets as it does for references (`io/importer.py` `_Row.derived_code`, `io/tables.py` `row_key`, the exporter writes no `code` cell). Generic code, no academic words. Tests: round trip of a resource sheet with `key_from`; a duplicate pair is placed on its last key column; renaming a key part renames the code and the references that use it, or is refused as a code change is today (check what the table editor does for a Session row and do the same).
- [ ] P28.3 **The academic preset.** `types.py`, `sheets.py` (`SHEETS_V2`: Programmes `university*`, Levels with `key_from=("programme", "level")`, Modules without `programmes`, Groups `level*` mapped to `parent`), `configuration.py` (who takes a module: by the group's level; drop `programmes_of` and the "programme belongs to level" check; messages from P28.1), `labels.py`. Tests first: one test per rule of "who takes a module", one per new message. The demands of a small hand-built dataset are the same as before when no module is shared.
- [ ] P28.4 **The L6 configuration fixture.** `tests/fixtures/l6-config/make_config.py`: one university (`UOW`, recorded as an assumption in `_meta`), programmes `CS` and `SE`, levels `CS-L6` and `SE-L6`, groups under their level. The shared modules `6COSC021C` and `6ELEN018C` become `6COSC021C-CS`, `6COSC021C-SE`, `6ELEN018C-CS` and `6ELEN018C-SE`, with their Session rows, group `options` and teacher `modules`. Regenerate `l6-config.xlsx`, `README.md` and `expected_demands.json`. **This change of expectation is the user's decision (2026-10-12), not a loosened test:** the two shared modules no longer make joint CS + SE sessions. Record the session count before (72) and after in `docs/LOG.md`, and check the run still has 0 hard violations (`test_l6_config.py`, `test_l6_fairness.py`).
- [ ] P28.5 **Migration `0006_programme_levels.py`** (a copy of the old reading, not imported from the preset, as `0005`). For each configured dataset: each programme takes the university of its old level as its parent (blank if none; then pre-flight reports it); for each programme a level `<programme>-<old level code>` is made under it; each group moves to its programme's new level; a module with one programme moves to that programme's level; **a module with several programmes is split** into `<module>-<programme>`, with its Session rows, group `options` and teacher `modules` rewritten. Before writing it, list what else can name a module or a level code in a stored dataset (constraint scopes such as `ref:`/`code:`, timetable edits of `<module>-<kind>` sessions). **Stop and ask** if anything other than those rows names a split module. Test on a database at revision 0005 with a shared module, a module with one programme and a group with options.
- [ ] P28.6 **Tables in the order they can be filled.** `SheetDef.section` (a generic name of the group the sheet belongs to; the preset gives the section labels). Version 2 order and sections as in the table above. A test for every preset: each column's `refs` and `suggests` name only sheets that come earlier, so a user who fills the tabs left to right, top to bottom, never needs a table they have not reached (version 1 and exams: only their order may change, never their columns; if their order already passes, leave it). Export writes sheets in this order (spec 03 §1 rule 13). Web: the tabs are rows, one per section, each with its section label, and Activities is in the last section. An empty table names the earlier tables it needs that are still empty ("Fill Programmes first: Levels refers to it").
- [ ] P28.7 **Field help.** `ColumnDef.help` and `SheetDef.help`: one plain sentence, given by the preset for every column and sheet that the app shows (a test fails on a missing one). The schema API serves them. Web: an info icon in each column header and on the entry row field (a Radix tooltip, opened by hover and by keyboard focus, `aria-describedby` on the field) that shows the help, then the format (from the column kind: "whole number ≥ 1", "time, HH:MM, 24-hour", "list, separated by ;"), whether it is required, its default, and the table it refers to. One info icon beside the table title shows the sheet's help. **One source:** the wiki's "Meaning" cell for a column must start with `help` (extend `test_wiki_tables.py`), so the wiki and the app cannot drift.
- [ ] P28.8 **Inputs audit (stop and ask).** List every column of every preset with its kind and what the user must know to type it (`docs/plan/phase-28-inputs.md`): the table above is the start. For each, propose an editor: a time picker, a date picker, a unit and minimum on int fields, labels on choices, suggestions from values used elsewhere (`room_type`), a module-and-kind picker (`Teachers.modules`), a form for `Constraints.params` built from the catalogue's parameters, syntax help and a live check for `Constraints.scope`, `*` offered on `Availability.period`, and the inherited value shown grey in a blank Session cell. Check how the exams preset checks `Days.code` today: if it does not already require `YYYY-MM-DD`, a `date` column kind would make imports stricter, which is a format change (ask). Check whether a date picker library is worth adding or a small one built on Radix `Popover` is enough (an ADR if a library is added; pin it exactly, as ADR-0009). Ask the user which editors to build now.
- [ ] P28.9 **Time and date inputs.** The `time` kind gets a picker: a field that shows `HH:MM` as its placeholder and accepts typing, and a popover with hours `00`–`23` and minutes (step from the existing periods, default 5). Always 24-hour, whatever the browser's locale (no native `<input type="time">`, which shows 12-hour on some systems). The entry row and the cell check the format before saving and say what is wrong (`"9.30" is not a time; use HH:MM, 24-hour, for example 09:30`); `end` after `start` is checked on the row. If P28.8 approves a `date` kind: a calendar popover for `YYYY-MM-DD`, the importer checks the format, and the exams `Days.code` uses it. Vitest for typing, picking, keyboard use and the messages; e2e on Periods.
- [ ] P28.10 **The other inputs approved in P28.8**, each with vitest cases, through `components/ui/` only (`raw-controls.test.ts` stays green). Server-side checks stay authoritative: the web checks only repeat them earlier.
- [ ] P28.11 **Wiki.** Tables overview (sections and their order, the hierarchy picture), the pages of Universities, Programmes, Levels (no code column, derived code), Modules (no `programmes`), Groups (`level`), Session types (room type suggestions), the glossary, the Tables tab page (grouped tabs, info icons, pickers), troubleshooting for the new messages (`test_wiki_troubleshooting.py` reproduces them), and `pnpm wiki:shots`.
- [ ] P28.12 **Full check.** `uv run ruff check . && uv run ruff format --check . && uv run mypy src && uv run pytest -m "not scale"`; `pnpm lint && pnpm typecheck && pnpm test && pnpm e2e`; `docker compose up --build` with migration `0005 -> 0006` on the PostgreSQL volume and `scripts/smoke.sh` on both paths.

## Acceptance
- In a configured dataset, Programmes have a university, Levels a programme, Modules and Groups a level. The Levels table has no `code` column, and `CS` + `L6` gives `CS-L6`.
- The order test passes for every preset: no table refers to a later one. The web tabs show the sections in that order.
- Every column and sheet shown in the app has a help sentence; the info icon shows it with the format, the default and the table it refers to; the wiki's "Meaning" cells start with the same sentences.
- A time can only be saved as `HH:MM` (24-hour), and a wrong value is explained before the save; the picker works by mouse and by keyboard.
- The L6 configuration, rebuilt, solves with 0 hard violations; the session counts before and after are in the log. The L6 fixture (`expected.json`), the exams fixture and every version 1 file are unchanged and green.
- Migration `0006` converts a stored configured dataset, including a shared module, and the Docker smoke test passes on both paths.
- No test or acceptance criterion was loosened.
