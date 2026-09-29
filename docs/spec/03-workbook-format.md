# 03 — Workbook Format (Import/Export Contract)

Status: **Authoritative. This is a contract.** Current `format_version`: **1**. Any change bumps the version and needs a note in `docs/STATUS.md`.

Code: `backend/src/timetabler/io/workbook.py`. The sheet definitions come from the preset (`02-domain-model.md` §6). This file specifies the `academic_weekly` preset.

## 1. General rules

1. **Container.** Either one `.xlsx` workbook with one sheet per table, or a `.zip` of UTF-8 CSV files named `<Sheet>.csv` with the same columns.
2. **Headers.** Row 1 holds the headers, exactly as specified (case-sensitive). Column order is free on import and fixed on export.
3. **Extra columns.** Headers starting with `x_` are user notes. They are kept through a round trip and ignored by the engine. Any other unknown header is an error.
4. **Codes.** Every entity row has a `code` that is unique within its sheet. Relationships refer to codes. Codes are trimmed, and matching is case-sensitive.
5. **Lists.** `;` separates list items. `key=value` pairs separate with `;` (for example `university=UOW;room_type=Lab`).
6. **Join sheets are canonical.** Convenience list columns (for example `groups` on Activities) are expanded into join rows on import. Export writes join sheets only.
7. **Blank values.** Empty cells mean null, or the default where one is stated.
8. **Booleans.** `true`/`false` (case-insensitive) and `1`/`0`.
9. **Times.** `HH:MM`, 24-hour.
10. **Atomic import.** Validate everything first and collect **all** errors. If there are any, import nothing.
11. **Error format.** `<Sheet>!R<row>C<col> [<column>]: <message>`, for example `ActivityGroups!R12C2 [group]: unknown code "L6 SE / G12"`.
12. **Round trip.** `export(import(wb)) == canonical(wb)`, and `import(export(ds)) == ds`.
13. **Export extras.** Exported `.xlsx` files have frozen header rows, data-validation dropdowns on reference columns, and sheets in the order below.

## 2. Sheets (`academic_weekly`, format_version 1)

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
| Format version | `_meta: format_version 2 not supported (max 1)` |

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
