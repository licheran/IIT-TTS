# Phase 21 — Academic configuration: workbook format version 2

**Goal:** an administrator configures a term with session types, modules, programmes, groups and teachers, in the workbook or on the Tables tab, and the academic preset turns it into demands.

## Read first
- `docs/spec/03-workbook-format.md` §2 (version 2) and §3, `docs/spec/02-domain-model.md` §6.1
- `backend/src/tts/presets/academic_weekly/`, `io/importer.py`, `io/tables.py`, `core/sheets.py`, `store/models.py`, `store/repositories.py`

## Tasks
- [x] P21.1 Sheet definitions for version 2 (configuration only):
  - **SessionTypes:** `code*` (the kind, for example `LEC`), `name`, `start_pattern*` (→StartPatterns; gives the length), `delivery` (`in_person` or `online`, default `in_person`), `room_type` (required when in person, blank when online), `max_groups` (the number of groups per session, whole number ≥ 1; blank means all the module's groups together), `teachers` (how many per session, default 1, 0 allowed), `weekly` (sessions per week, default 1; a group keeps the same companions every time), `tags`;
  - `Modules.level`: exactly one level (→Levels), required;
  - `Modules.programmes`: the degrees at that level that take the module (list of →Programmes whose level is the module's level); blank means every programme at the level. It replaces today's information-only `programme`;
  - `Modules.optional`: true or false, default false (mandatory);
  - `Modules.sessions`: a list of kinds. Each item may override SessionTypes columns for this module, for example `LEC, LAB(start_pattern=3H, max_groups=2)`;
  - `Teachers.modules`: a list of `module` (every kind) or `module:KIND` (only that kind);
  - `Groups.parent`: a programme only (a group under a group is refused);
  - `Groups.options`: the group's optional modules (a group is students who share the same options). Each must be an optional module of the group's level and programme;
  - no Templates, Activities, ActivityGroups, ActivityTeachers, Pins or Assignments sheets.

  Validation messages from spec 03 §3. `format_version` 2 for `academic_weekly` and still 1 for `exams`: the maximum version is per preset.
- [x] P21.2 The preset turns configuration into demands (a pure function, in the preset):
  - one demand per module and session kind;
  - participants: for a mandatory module, every group under the module's programmes at its level; for an optional module, only those groups that list it in `options`;
  - pooled Room: `tag:room_type=<t>`, `sum_of_fixed:StudentGroup`. None when online;
  - pooled Teacher: count from `teachers`, filter `code:` the module's teachers for that kind;
  - `repeat` from `weekly`, `max_participants` from `max_groups`, and the start pattern from the session type or its override.

  Tests:
  - mandatory only;
  - a mandatory module limited to one programme;
  - an optional module taken by some groups;
  - import errors: a group listing a mandatory module or a module from another level in `options`; a module whose `programmes` are at another level; a group whose parent is a group;
  - a kind limited to some teachers;
  - online kinds;
  - overrides.
- [x] P21.3 Version 1 files still import, into a **hand-made** dataset:
  - Activities with ActivityGroups and ActivityTeachers become events with fixed resources;
  - Pins become pins;
  - a Templates sheet with rows is expanded once, by `expand/`, into events, and a note says so;
  - a hand-made dataset exports as version 1, and a configured dataset as version 2.

  Tests: `l6.xlsx` imports to the same dataset as today, exports as version 1 losslessly, and `expected.json` still passes. `templates.xlsx` imports to the fixture's activity counts.
- [x] P21.4 Store, API and migration:
  - tables or columns for session types, the module's level, programmes, optional flag and sessions, teacher modules and group options;
  - the dataset's kind: configured or hand-made;
  - the dataset read and write endpoints; the OpenAPI types regenerated for the web.

  Integration tests on SQLite and PostgreSQL (`TT_TEST_PG`).
- [x] P21.5 The Tables tab:
  - Session types as a new table;
  - the new columns in Modules, Teachers and Groups, with the entry row, and suggestions for module codes and kinds. The `options` suggestions list only the optional modules of the group's level and programme;
  - a new academic dataset is configured by default; a hand-made dataset (for example L6) keeps its Activities, with groups and teachers as columns;
  - a read-only **Sessions to schedule** view on the Pre-flight tab: each module and kind, its groups, the number of blocks and the sessions per week.

  Vitest tests, and an e2e test that configures one module with two groups and runs it.
- [x] P21.6 A new fixture `backend/tests/fixtures/l6-config/l6-config.xlsx`: L6 written as configuration. It has the same modules, groups, rooms and teachers; session types taken from the L6 activities; teacher pools from ActivityTeachers; and assumptions in `_meta`. An end-to-end test through the CLI and the API: it imports, passes pre-flight, solves within the P20.8 target, verifies with 0 hard violations and exports its results.
- [x] P21.7 Wiki:
  - pages for SessionTypes and the changed tables (the drift tests in `test_wiki_tables.py` require them);
  - the version 2 import messages in the troubleshooting pages (`test_wiki_troubleshooting.py`);
  - the Import / export tab page: what the version 2 workbook holds and doesn't hold.

## Acceptance
- `l6-config.xlsx` imports, solves and verifies through the CLI, the API and the web UI, with 0 hard violations, within the P20.8 target.
- `l6.xlsx` (version 1) still imports, solves and meets `expected.json`.
- The exams preset is unchanged, and its fixture still passes.
