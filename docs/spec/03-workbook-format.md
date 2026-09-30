# 03 — Workbook Format (Import/Export Contract)

Status: **Authoritative. This is a contract.** Current `format_version`: **2** for configured `academic_weekly` datasets (§2a), **1** for hand-made `academic_weekly` datasets (§2) and for `exams`. The maximum version is per preset. Any change bumps the version and needs a note in `docs/STATUS.md`. A version 2 workbook holds **configuration only**: no timetable, no edits (ADR-0007).

Code: `backend/src/tts/io/workbook.py`. The sheet definitions come from the preset (`02-domain-model.md` §6). This file specifies the `academic_weekly` preset.

## 1. General rules

1. **Container.** Either one `.xlsx` workbook with one sheet per table, or a `.zip` of UTF-8 CSV files named `<Sheet>.csv` with the same columns.
2. **Headers.** Row 1 holds the headers, exactly as specified (case-sensitive). Column order is free on import and fixed on export.
3. **Extra columns.** Headers starting with `x_` are user notes. They are kept through a round trip and ignored by the engine. Any other unknown header is an error.
4. **Codes.** Every entity row has a `code` that is unique within its sheet. Relationships refer to codes. Codes are trimmed, and matching is case-sensitive.
5. **Lists.** `;` separates list items. `key=value` pairs separate with `;` (for example `university=UOW;room_type=Lab`).
6. **Join sheets are canonical (version 1).** Convenience list columns (for example `groups` on Activities) are expanded into join rows on import. Export writes join sheets only. Version 2 has no join sheets.
7. **Blank values.** Empty cells mean null, or the default where one is stated.
8. **Booleans.** `true`/`false` (case-insensitive) and `1`/`0`.
9. **Times.** `HH:MM`, 24-hour.
10. **Atomic import.** Validate everything first and collect **all** errors. If there are any, import nothing.
11. **Error format.** `<Sheet>!R<row>C<col> [<column>]: <message>`, for example `ActivityGroups!R12C2 [group]: unknown code "L6 SE / G12"`.
12. **Round trip.** `export(import(wb)) == canonical(wb)`, and `import(export(ds)) == ds`.
13. **Export extras.** Exported `.xlsx` files have frozen header rows, data-validation dropdowns on reference columns, and sheets in the order below.

## 2. Sheets (`academic_weekly`, format_version 1: hand-made datasets)

Version 1 is what hand-made datasets (typed or imported activities, such as the L6 fixture) import and export. A version 2 file cannot hold their events.

`*` = required · `→X` = code reference to sheet X

| Sheet | Columns |
|---|---|
| `_meta` | `key*`, `value`. Required keys: `format_version`, `preset`. Optional: `institution`, `exported_at`, `assumptions` (free text) |
| `Days` | `code*`, `label`, `order*` |
| `Periods` | `code*`, `start*`, `end*`, `order*`, `is_break` (default false) |
| `StartPatterns` | `code*`, `duration*`, `start_periods*` (list of →Periods), `days` (list of →Days, default all) |
| `Universities` | `code*`, `name`, `tags` |
| `Levels` | `code*`, `name`, `university` (→Universities), `tags` |
| `Programmes` | `code*`, `name`, `level` (→Levels), `tags` |
| `Groups` | `code*`, `name`, `parent*` (→Programmes or →Groups), `size` (int ≥ 0), `tags` |
| `Teachers` | `code*`, `name`, `tags` |
| `Campuses` | `code*`, `name`, `tags` |
| `Buildings` | `code*`, `name`, `abbreviation`, `campus` (→Campuses), `tags` |
| `Rooms` | `code*`, `name`, `building` (→Buildings), `capacity` (int ≥ 0), `room_type*`, `tags` |
| `Modules` | `code*`, `name`, `level` (→Levels), `programme` (→Programmes), `tags` |
| `Templates` | `code*`, `module*` (→Modules), `kind*`, `mode*` (`joint`\|`per_group`\|`batched`), `groups*` (selector), `batch_size` (required if batched), `teachers` (list of →Teachers), `duration*`, `start_pattern*` (→StartPatterns), `room_type` (blank means online), `sessions_per_week` (default 1), `active` (default true) |
| `Activities` | `code*`, `module` (→Modules), `kind*`, `duration*`, `start_pattern*` (→StartPatterns), `delivery` (default `in_person`), `room_type`, `room_count` (default 1; 0 if online), `template` (→Templates, set by the expander), `groups` (convenience list), `teachers` (convenience list), `tags` |
| `ActivityGroups` | `activity*` (→Activities), `group*` (→Groups, →Programmes or →Levels) |
| `ActivityTeachers` | `activity*` (→Activities), `teacher*` (→Teachers) |
| `Availability` | `resource*` (any resource code), `day*` (→Days), `period*` (→Periods, or `*` for the whole day), `status*` (`unavailable`\|`avoid`) |
| `Constraints` | `code*`, `type*` (catalogue type), `scope*` (selector), `params` (JSON object), `hard` (default true), `weight` (default 1), `active` (default true) |
| `Pins` | `activity*` (→Activities), `day` (→Days), `start_period` (→Periods), `rooms` (list of →Rooms), `source` (default `user`) |
| `Assignments` (export only) | `run`, `activity`, `module`, `kind`, `day`, `start`, `end`, `rooms`, `groups`, `teachers`, `buildings` |

### 2.1 Mapping to core (for implementers)

- Universities, Levels, Programmes, Groups, Teachers, Campuses, Buildings and Rooms become `resource` rows of the matching type.
- Parents: Level→University, Programme→Level, Group→(Programme|Group), Building→Campus, Room→Building.
- `Groups.size` and `Rooms.capacity` become `resource.capacity`.
- `Rooms.room_type` becomes the tag `room_type=<value>`.
- Modules become `reference` rows.
- Activities become `event` rows.
  - ActivityGroups and ActivityTeachers become fixed requirements.
  - `room_type`/`room_count` become a pooled Room requirement with filter `tag:room_type=<room_type>` and capacity rule `sum_of_fixed:StudentGroup`.

## 2a. Sheets (`academic_weekly`, format_version 2: configured datasets)

`*` = required · `→X` = code reference to sheet X · `(new)` and `(changed)` are relative to §2.

| Sheet | Columns |
|---|---|
| `_meta` | As version 1, with `format_version` 2 |
| `Days`, `Periods`, `StartPatterns` | As version 1 |
| `Universities`, `Levels`, `Programmes`, `Campuses`, `Buildings`, `Rooms` | As version 1 |
| `Groups` (changed) | `code*`, `name`, `parent*` (→Programmes **only**), `size` (int ≥ 0), `options` (new: list of →Modules; the group's optional modules), `tags` |
| `Teachers` (changed) | `code*`, `name`, `modules` (new: list of →Modules, or `module:KIND` to teach only that session kind), `tags` |
| `Modules` (changed) | `code*`, `name`, `level*` (→Levels; exactly one), `programmes` (new: list of →Programmes whose level is the module's level; blank = every programme at the level), `optional` (new: bool, default false = mandatory), `sessions` (new: list of →SessionTypes, each with optional settings, see below), `tags` |
| `SessionTypes` (new) | `code*` (the kind, for example `LEC`), `name`, `start_pattern*` (→StartPatterns; it gives the length), `delivery` (`in_person`\|`online`, default `in_person`), `room_type` (required when in person, blank when online), `max_groups` (int ≥ 1; blank = all the module's groups in one session), `teachers` (int ≥ 0, default 1: teachers per session), `weekly` (int ≥ 1, default 1: sessions per week), `tags` |
| `Availability`, `Constraints` | As version 1 |

Not in version 2: `Templates`, `Activities`, `ActivityGroups`, `ActivityTeachers`, `Pins`, `Assignments`. A file with one of them is refused (`<Sheet>: unknown sheet`).

**`Modules.sessions`.** Items are separated by `;`. An item is a session type code, optionally followed by settings in parentheses, `name=value` pairs separated by `,`, which override that session type for this module. The settings are `start_pattern`, `delivery`, `room_type`, `max_groups`, `teachers` and `weekly`. Example: `LEC;TUT;LAB(start_pattern=3H,max_groups=2)`.

**`Teachers.modules`.** `6BUIS019C` means the teacher may take every session kind of that module; `6BUIS019C:TUT` means tutorials only. Several items are separated by `;`.

**Who takes a module.** A mandatory module is taken by every group under its `programmes` (every programme of its level when blank). An optional module is taken only by the groups that list it in `options`.

**Blocks and sessions.** For each module and session kind, the taking groups are split by the solver into `⌈groups / max_groups⌉` blocks of nearly equal size (10 groups with `max_groups` 3 give 3 + 3 + 2 + 2). Each block has `weekly` sessions a week, always with the same groups. The room must seat all the students of the block.

## 3. Validation (import)

| Rule | Error example |
|---|---|
| Required column missing | `Rooms!R1 [capacity]: missing column` |
| Required value blank | `Activities!R7C3 [kind]: required` |
| Duplicate code | `Teachers!R40C1 [code]: duplicate "HAWE" (first at R12)` |
| Unknown reference | `ActivityTeachers!R8C2 [teacher]: unknown code "HAWEE"` |
| Bad type or range | `Rooms!R4C4 [capacity]: expected integer ≥ 0, got "thirty"` |
| Bad selector or JSON | `Constraints!R3C3 [scope]: unknown clause "teacher:"` |
| Unknown constraint type | `Constraints!R5C2 [type]: "max_gap" is not in the catalogue` |
| Hierarchy cycle | `Groups!R10C3 [parent]: cycle L6 SE / G1 → … → L6 SE / G1` |
| Format version | `_meta: format_version 3 not supported (max 2)` |

Version 2 adds:

| Rule | Error example |
|---|---|
| Module without a level | `Modules!R4C3 [level]: required` |
| Module programme at another level | `Modules!R4C4 [programmes]: programme "L5 CS" belongs to level "L5", not "L6"` |
| Bad flag | `Modules!R4C5 [optional]: expected true or false, got "maybe"` |
| Unknown session type | `Modules!R4C6 [sessions]: unknown code "LAB"` |
| Unreadable setting | `Modules!R4C6 [sessions]: cannot read "LAB(start_pattern)": expected name=value` |
| Unknown setting | `Modules!R4C6 [sessions]: unknown setting "size" (known: start_pattern, delivery, room_type, max_groups, teachers, weekly)` |
| Teacher for a kind the module lacks | `Teachers!R9C3 [modules]: "6SENG005C:LAB": module "6SENG005C" has no session type "LAB"` |
| Group under a group | `Groups!R10C3 [parent]: must be a programme, got group "L6 CS / G1"` |
| Option that is not optional | `Groups!R10C5 [options]: module "6SENG005C" is not optional` |
| Option at another level | `Groups!R10C5 [options]: module "5SENG001C" is at level "L5", the group is at level "L6"` |
| Option not offered to the programme | `Groups!R10C5 [options]: module "6SENG012C" is not offered to programme "L6 CS"` |
| Online session type with a room type | `SessionTypes!R3C5 [room_type]: an online session cannot have a room type` |
| In-person session type without one | `SessionTypes!R3C5 [room_type]: required unless delivery is online` |
| Bad number | `SessionTypes!R3C6 [max_groups]: expected integer ≥ 1, got "0"` |
| A file of one version with another's sheet | `Activities: unknown sheet` |

## 4. Example rows (from the L6 fixture)

```
Periods:        P01, 08:30, 09:30, 1, false   …   P05, 12:30, 13:30, 5, true
StartPatterns:  2H, 2, P01;P03;P06;P08;P10
Groups:         L6 SE / G1, , L6 SE, 30,
Rooms:          [2LA] -GP, , GP, 90, lab,
Activities:     6SENG005C-TUT-01, 6SENG005C, TUT, 2, 2H, in_person, lab, 1, , L6 SE / G1, HAWE;HARR,
Constraints:    C-GAPS, max_gaps, type:StudentGroup, {"max": 2, "per": "day"}, false, 5, true
```

(The teacher codes in the example row are illustrative. The fixture holds the real values.)

Version 2 example rows (from `tests/fixtures/l6-config/`, derived from the L6 fixture):

```
SessionTypes:   LEC, Lecture, 2H, in_person, lab, 7, 1, 1,
SessionTypes:   TUT, Tutorial, 2H, in_person, lab, 1, 1, 1,
Modules:        6SENG005C, , L6, L6 SE, false, LEC;TUT,
Teachers:       HAWE, , 6SENG005C:LEC;6SENG005C:TUT,
Groups:         L6 SE / G1, , L6 SE, 30, ,
```
