# L6 as configuration (workbook format version 2)

`l6-config.xlsx` is the L6 dataset written the way a configured dataset is: no activities, only the
configuration. The solver makes the sessions.

Regenerate it with `uv run python tests/fixtures/l6-config/make_config.py` (from `backend/`). A test
checks that the committed file equals the script's output.

`expected_demands.json` holds the 20 demands (72 sessions) this configuration made when each
module kept its sessions in an inline `Modules.sessions` list. A test checks that the Session table
derives exactly the same demands.

How the real L6 export became configuration (also in the workbook's `_meta` sheet):

- Session types `LEC` and `TUT` hold the settings most modules of that kind share. The `Session`
  sheet has one row for each module and session type, and fills only the cells where the module
  differs, for example `max_groups` 4 on a lecture, or `delivery` online with `max_groups` 1.
- The groups of a module are the groups that attended any of its activities.
- `max_groups` is the most groups any one activity of that module and kind had.
- A module is mandatory when every group of its programmes takes it, and optional otherwise; each
  group that takes an optional module lists it in `options`.
- A teacher lists the modules they taught (`module:KIND` when only some kinds), and the solver
  chooses among them: one teacher per session.

Group size 30, room capacities and types, and the break period are the assumptions of `../l6/`.
The real activities are 77 (22 LEC, 55 TUT); the configuration makes 72 sessions, because groups are
now split by the solver instead of copied from the export.
