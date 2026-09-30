# Phase 24 — The Session table: a module's sessions, one row per session type

**Goal:** a module's sessions are configured in their own table, **Session**, with one row per module and session type, and not in the inline `Modules.sessions` list (`LEC;TUT;LAB(start_pattern=3H,max_groups=2)`). A row names the module and the session type. Any setting left blank comes from the session type, and a filled cell overrides it for that module only. For example, a module's lecture can allow four groups per session while its tutorial keeps the session type's one group.

**Decided by the user (2026-09-30):**
- the table is named `Session`;
- `Teachers.modules` stays as it is (`module` or `module:KIND`);
- workbook format version 2 is **amended**, with no bump to version 3. No version 2 file exists outside this repository, and the only one inside it is the `l6-config.xlsx` fixture, which is regenerated.

## Read first
- `docs/adr/0007-solver-decided-sessions.md` (Decision, academic workbook format version 2; and the amendment)
- `docs/spec/03-workbook-format.md` §2a (the version 2 sheets, `Modules.sessions`) and §3 (validation messages)
- `docs/spec/02-domain-model.md` §6.1 (academic configuration mapping)
- `backend/src/tts/presets/academic_weekly/{sheets,types,configuration}.py`, `backend/src/tts/io/importer.py`, `backend/tests/fixtures/l6-config/make_config.py`

## The table (proposal, confirmed in P24.1)

Sheet `Session`, placed after `Modules` in the workbook (it refers to Modules and SessionTypes):

| Column | Type | Required | Meaning |
|---|---|---|---|
| `module` | text, →Modules | yes | The module |
| `session_type` | text, →SessionTypes | yes | The kind of session (`LEC`, `TUT`, your own) |
| `start_pattern` | text, →StartPatterns | no | Blank: the session type's. Gives the length and the allowed starts |
| `delivery` | `in_person` \| `online` | no | Blank: the session type's |
| `room_type` | text | no | Blank: the session type's. Never used when the session is online |
| `max_groups` | whole number ≥ 1 | no | Groups per session. Blank: the session type's |
| `teachers` | whole number ≥ 0 | no | Teachers per session. Blank: the session type's |
| `weekly` | whole number ≥ 1 | no | Sessions per week for each group. Blank: the session type's |
| `tags` | key=value pairs | no | Added to the session's tags, winning over the session type's and the module's |

- The key is (`module`, `session_type`). A second row with the same pair is an error.
- A module has the sessions its rows list. A module with no rows makes no sessions.
- `Modules.sessions` is removed. Modules keep `code`, `name`, `level`, `programmes`, `optional` and `tags`.
- The demand of a row keeps the code `<module>-<session_type>`, so the edits of Phase 22 and the session codes (`<module>-<kind>-<nn>`) do not change.

## Tasks
- [ ] P24.1 **Stop and ask**, then update the documents:
  - confirm the columns above, the sheet position, the tab label (`Session`) and the rule for a blank cell;
  - confirm what a module with no Session rows is: a pre-flight warning (proposed), or an error;
  - confirm that the glossary keeps **session** for one meeting in the timetable, and describes a **Session row** as "how a module holds one kind of session" (both names are in use from now on);
  - then update ADR-0007 (the amendment), spec 03 §2a and §3 (the new sheet and its messages; `Modules.sessions` removed; the amendment noted), spec 02 §6.1 (the mapping), spec 01 FR-17 (the wording), spec 06 if a table or endpoint changes, and a STATUS note for rule 4 (format change: version 2 amended, not bumped, approved by the user).
- [ ] P24.2 Sheet definition and storage:
  - add `Session` to `SHEETS_V2` (`presets/academic_weekly/sheets.py`) and remove the `sessions` column from Modules;
  - store each row in the existing attribute storage. The proposal is a reference of a new type `Session` whose code is derived from its key (`<module>-<session_type>`), with the other columns as attributes, so that no new database table is needed;
  - if the sheet framework (`core/sheets.py`, `io/importer.py`, `io/tables.py`) cannot key a reference sheet on two columns without a user-visible `code` column, **stop and ask** before choosing another way.

  Tests: the sheet definition (`test_sheet_definitions_v2.py`), a round trip of the new sheet (xlsx and CSV zip), and a duplicate (module, session_type) refused with its row and column.
- [ ] P24.3 Demands from Session rows (`presets/academic_weekly/configuration.py`):
  - `demands(dataset)` reads the Session rows. Each setting is the row's value, or else the session type's;
  - an online row never gets a room requirement, even when its session type has a room type;
  - an in-person row whose session type is online must give a `room_type`;
  - `configuration_issues` checks, with messages placed on the row and column: an online row with a `room_type`; an in-person row with no room type (neither its own nor its session type's); `Teachers.modules` `module:KIND` against the module's Session rows (the message `module "M" has no session type "K"` stays);
  - the six `Modules.sessions` messages (`unknown setting`, `cannot read … expected name=value`, and the rest) are removed with the parser (`parse_session_item`);
  - a module with no Session rows is reported as agreed in P24.1.

  Tests: every setting inherited and every setting overridden; the tags order (session type, then module, then row); each new message; and **a regression: the demands derived from the rebuilt `l6-config.xlsx` equal those derived today** (the same codes, participants, limits, repeats, durations and pooled requirements; 72 sessions).
- [ ] P24.4 Import, export and stored data:
  - a version 2 file with a `Modules.sessions` column is refused (`Modules!R1C6 [sessions]: unknown column`);
  - `_meta.format_version` stays 2;
  - a data migration turns the `sessions` attribute of stored configured datasets into Session rows, using the same parsing as today, and then drops the attribute. It is tested on a database at the previous revision, as `0004_expand_templates` was;
  - table edits (`api/workbooks.py`) keep a configured dataset's edits when a Session row changes (`keep_edits`).

  Tests: import and export of the new sheet through the API, and the migration test.
- [ ] P24.5 Fixture `backend/tests/fixtures/l6-config/`:
  - `make_config.py` writes one Session row per module and kind, filling only the cells that differ from the session type (for example `max_groups` 4 on a lecture, `delivery` online on the online lecture);
  - regenerate `l6-config.xlsx` and update the README and the `_meta` assumptions;
  - `test_l6_config.py` still passes: the workbook equals the script's output, the CLI solves it with 0 hard violations, and the API solves it, keeps an edit through a rebuild and exports it.
- [ ] P24.6 Web:
  - the Tables tab shows **Session** (schema-driven), with the entry row, and dropdowns for `module`, `session_type`, `start_pattern` and `delivery`;
  - a blank cell shows the inherited value in grey, if it can be done without a special case per column. Otherwise leave it blank, and the wiki says where the value comes from;
  - pre-flight links on a Session issue open the Session row;
  - regenerate the OpenAPI types if the schema changes.

  Tests: vitest where a component changes, and `web/e2e/configured.spec.ts` extended: change one Session row's `max_groups`, and see the **Sessions to schedule** count change on the Pre-flight tab.
- [ ] P24.7 Wiki:
  - a new page `docs/wiki/tables/Session.md` (the drift test in `test_wiki_tables.py` requires it) with the columns, the blank-means-inherited rule, and an example of a lecture with several groups and a tutorial with one;
  - the Modules page loses `sessions`; the SessionTypes page explains that its values are defaults a Session row can override;
  - the tables overview (the diagram, the order of the workbook, the order to fill in), the Tags page, the glossary, and the Activities and Pre-flight tab pages;
  - the troubleshooting page: the removed `Modules.sessions` messages replaced by the Session messages, each reproduced by `test_wiki_troubleshooting.py`;
  - redraw the pictures that show the tables (`pnpm wiki:shots`).
- [ ] P24.8 The full check:
  - backend and web checks, and `pnpm e2e`;
  - `docker compose up --build` with `scripts/smoke.sh` (both paths);
  - L6 (`expected.json`) and the exams fixture unchanged;
  - tick the boxes, log STATUS, commit and push.

## Acceptance
- A version 2 academic workbook has a `Session` sheet and no `Modules.sessions` column, and its `format_version` is still 2.
- The rebuilt `l6-config.xlsx` imports, passes pre-flight, solves and verifies (0 hard violations) through the CLI, the API and the web UI, and derives exactly the same demands as before the change.
- A module's lecture and tutorial can have different groups per session, set per module in the Session table, with nothing typed inline.
- Hand-made datasets (version 1, `l6.xlsx`, `templates.xlsx`) and the exams preset are unchanged.
- The wiki drift tests pass.
