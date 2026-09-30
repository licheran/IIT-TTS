# Phase 14 — Wiki: table reference (academic preset)

**Goal:** one page for every table (sheet) of the academic preset, with each column's meaning, data type, whether it is mandatory, its default, and what it refers to. Plus a page on how tags work.

## Read first
- `docs/spec/03-workbook-format.md` §2 (the sheets)
- `docs/spec/02-domain-model.md` §2 (resources, tags), §5 (selectors) and §6.1 (academic mapping)
- `backend/src/tts/presets/academic_weekly/sheets.py` (`SHEETS`, the `ColumnDef` fields)
- `backend/src/tts/core/sheets.py` (what `kind`, `required_when`, `refs`, `choices`, `allow_star` and `stored_as` mean)

## Tasks
- [ ] P14.1 `tables/README.md`: the sheet order, and a diagram of how sheets refer to each other:
  - University → Level → Programme → Group;
  - Campus → Building → Room;
  - Module, which Templates and Activities refer to;
  - Activities with ActivityGroups and ActivityTeachers;
  - Availability, Constraints and Pins.

  It also says which sheets are generated (Activities from Templates; Assignments is export-only).
- [ ] P14.2 One page per sheet, in workbook order: `_meta`, `Days`, `Periods`, `StartPatterns`, `Universities`, `Levels`, `Programmes`, `Groups`, `Teachers`, `Campuses`, `Buildings`, `Rooms`, `Modules`, `Templates`, `Activities`, `ActivityGroups`, `ActivityTeachers`, `Availability`, `Constraints`, `Pins`, `Assignments`. Each page has:
  - **What it is**, and when you edit it;
  - a **Columns** table: `Column | Meaning | Type | Required | Default | Allowed values or refers to`. Types are plain words: text, whole number, time (HH:MM), true/false, list, key=value pairs, selector, JSON. The source is `ColumnDef` plus spec 03 §2;
  - the rules that aren't obvious, for example:
    - `_meta` keys (`format_version`, `preset`, `institution`, `assumptions`);
    - `Periods.is_break`, and why an activity can't span a break;
    - `StartPatterns` `duration` vs `start_periods`;
    - a Group's parent may be a Programme or another Group;
    - `Rooms.room_type` is stored as a tag;
    - `Templates.mode` (joint, per_group, batched) and `batch_size`;
    - `Activities.delivery=online` means no room, `room_count`, and the `groups` and `teachers` convenience columns that become join rows;
    - `Availability` `period=*`, and unavailable vs avoid;
    - `Pins` with a day only, a day and period, or rooms, and `source=lock`;
    - `Assignments` columns that are derived;
  - an L6 example row;
  - the import errors the sheet typically produces (linked to Phase 16 once it exists).
- [ ] P14.3 `tables/tags.md`:
  - the `key=value;key=value` format;
  - which sheets have a `tags` column (every resource sheet, Modules and Activities);
  - that `room_type` is stored as the tag `room_type=<value>`;
  - how tags are used: `tag:k=v` and `tag:k!=v` in constraint scopes, template groups and room filters;
  - suggested conventions, clearly marked as suggestions (for example `university=UOW`, `floor=2`);
  - a table of each sheet, whether it accepts tags, and which tags the engine itself reads.
- [ ] P14.4 The tables check in `test_wiki.py`: each `SheetDef` in `SHEETS` has `tables/<Sheet>.md`. Its Columns table lists every `ColumnDef.name`, and its Required and Default cells match `required`, `required_when` and `default`. Every sheet with a `tags` column links to `tags.md`.

## Acceptance
- All 21 academic sheets are documented.
- Every column appears with a type, required mark and default that match the code (the check in P14.4 enforces it).
- `tags.md` is linked from every sheet that has a `tags` column.
