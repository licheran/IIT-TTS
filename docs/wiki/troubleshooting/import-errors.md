# Import and editing errors

## What it's for

When you import a workbook, or change a row in the table editor, the data is checked. If anything is wrong, **nothing is changed** and every problem is listed. This page explains each message, what caused it and how to fix it.

## How to read a message

```
ActivityGroups!R12C2 [group]: unknown code "L6 SE / G12"
```

| Part | Meaning |
|---|---|
| `ActivityGroups` | The sheet (table) |
| `R12` | Row 12 of that sheet. Row 1 is the header row, so the first data row is R2 |
| `C2` | Column 2, counting from the left and starting at 1 |
| `[group]` | The name of the column |
| the rest | What is wrong |

Some messages name only the sheet (`Foo: unknown sheet`) or the whole file (`workbook: …`).

**Fix the first messages first.** One mistake often causes several messages. For example, a duplicated teacher code that replaces another teacher's code makes every activity of the replaced teacher report `unknown code`. Fix, import again, and the rest often disappear.

## The file itself

| Message | Cause | Fix |
|---|---|---|
| `workbook: not a valid .xlsx file` | The file is not an Excel workbook, or it is damaged | Open it in Excel and save it again as `.xlsx`, or export from the app |
| `workbook: not a valid .zip file` | A CSV upload that is not a zip | Put the CSV files in a `.zip` |
| `workbook: file is larger than 20 MB` | The upload is too big | Remove unused rows or sheets |
| `workbook: the zip unpacks to too much data` | The zip is far bigger when unpacked | Use a normal export of the data |
| `<Sheet>: not valid UTF-8` | A CSV file is not saved as UTF-8 | Save the CSV as UTF-8 |
| `<Sheet>: unknown sheet` (for example `Foo: unknown sheet`) | The file has a sheet the preset does not have | Delete or rename the sheet. Sheets whose name starts with `_` are ignored. A workbook from the other preset shows this for every sheet that differs |

For a CSV zip, each file is named `<Sheet>.csv`, for example `Rooms.csv`.

## The `_meta` sheet

| Message | Cause | Fix |
|---|---|---|
| `_meta: sheet is missing` | No `_meta` sheet | Add it with the columns `key` and `value` |
| `_meta!R1: columns "key" and "value" are required` | The header row is wrong | Name the columns exactly `key` and `value` |
| `_meta!R4C1 [key]: required` | A row with a value but no key | Fill in the key or delete the row |
| `_meta!R6C1 [key]: duplicate "preset"` | The same key twice | Keep one |
| `_meta: "format_version" is required` | No `format_version` row | Add `format_version` with `1` |
| `_meta: format_version must be an integer, got "x"` | The value is not a whole number | Write `1` |
| `_meta: format_version 3 not supported (max 2)` | The file is from a newer format than this app reads | Export again from this app |
| `_meta: "preset" is required` | No `preset` row | Add `preset` with `academic_weekly` (or `exams`) |
| `_meta: unknown preset "nope"` | The preset name is not known | Use `academic_weekly` or `exams` |

## Headers and columns

| Message | Cause | Fix |
|---|---|---|
| `Rooms!R1C7 [colour]: unknown column` | A header the table does not have, and that does not start with `x_` | Fix the spelling, delete the column, or rename it `x_colour` to keep it as a note |
| `Rooms!R1 [room_type]: missing column` | A column the table needs is not in the header row | Add the column with exactly that name |
| `Rooms!R1C7 [capacity]: duplicate column (first at C4)` | The same header appears twice | Delete one |

Header names are case-sensitive and must match exactly.

## Values in cells

| Message | Cause | Fix |
|---|---|---|
| `Rooms!R2C5 [room_type]: required` | A required cell is empty | Fill it in |
| `Templates!R2C6 [batch_size]: required when mode is "batched"` | A column that is needed only in some cases is empty | Fill it in, or change the `mode` |
| `Rooms!R2C4 [capacity]: expected integer ≥ 0, got "thirty"` | A number column holds something else | Write digits only, for example `30` |
| `Groups!R2C4 [size]: expected integer ≥ 0, got "-1"` | The number is below the smallest allowed. The limit is in the message | Use a value at or above it |
| `Activities!R2C4 [duration]: expected integer ≥ 1, got "0"` | Same, for a column that must be at least 1 | Use 1 or more |
| `Periods!R2C2 [start]: expected HH:MM, got "8.30 am"` | A time is not `HH:MM` | Write it on the 24-hour clock: `08:30` |
| `Periods!R2C5 [is_break]: expected true or false, got "maybe"` | A true/false column holds something else | Write `true`, `false`, `1` or `0` |
| `Availability!R2C4 [status]: expected one of unavailable, avoid, got "sometimes"` | The value is not one of the allowed choices | Use one of the listed values |
| `Templates!R2C4 [mode]: expected one of joint, per_group, batched, got "weekly"` | Same, for `mode` | Use one of the listed values |
| `Periods!R2C3 [end]: end must be after start` | A period ends before it starts | Correct `start` or `end` |
| `Teachers!R2C3 [tags]: expected key=value pairs separated by ";", got "floor"` | A tag without `=` | Write `floor=2`. See [Tags](../tables/tags.md) |
| `Teachers!R2C3 [tags]: duplicate key "a"` | The same tag key twice in one row | Keep one |

## Codes and references

| Message | Cause | Fix |
|---|---|---|
| `Teachers!R3C1 [code]: duplicate "AAM" (first at R2)` | Two rows of one table share a code | Make the codes different |
| `ActivityTeachers!R2C2 [teacher]: unknown code "NOBODY"` | A cell names a code that is not in the table it refers to | Correct the spelling (codes are case-sensitive) or add the missing row |
| `StartPatterns!R2C3 [start_periods]: unknown code "P99"` | Same, for a list: one of the items is unknown | Correct the item |
| `Activities!R2C5 [start_pattern]: unknown code "9H"` | The start pattern does not exist | Add it to Start patterns, or change the activity |
| `Groups!R2C3 [parent]: required` | A group has no parent | Give it a programme or group |
| `Groups!R2C3 [parent]: cycle L6 CS / G1 → L6 CS / G10 → L6 CS / G1` | Parents loop back on themselves | Break the loop: a group cannot be its own ancestor |

Dropdowns in exported Excel files help avoid unknown codes.

## Constraints

| Message | Cause | Fix |
|---|---|---|
| `Constraints!R2C2 [type]: "max_gap" is not in the catalogue` | The type is not one of the fourteen | Use a type from the [constraint list](../constraints/README.md) |
| `Constraints!R2C3 [scope]: unknown clause "teacher:"` | The selector has a clause name that does not exist | See [Selectors](../constraints/selectors.md) |
| `Constraints!R2C3 [scope]: clause "kind:" does not select resources` | The selector picks the wrong kind of thing for this type | Use a clause that picks what the type covers |
| `Constraints!R2C4 [params]: expected a JSON object, got invalid JSON (Expecting property name enclosed in double quotes)` | `params` is not valid JSON | Use double quotes: `{"max": 2}` |
| `Constraints!R2C4 [params]: expected a JSON object` | `params` is valid JSON but not an object such as `{…}` | Write an object |
| `Constraints!R3C1 [code]: duplicate "X" (first at R2)` | Two constraints share a code | Make the codes different |
| `Constraints!R2C6 [weight]: expected integer ≥ 0, got "-1"` | A negative weight | Use 0 or more |

**Wrong or missing `params` are not caught at import.** `{"mx": 1}` or an empty `{}` for a type that needs `max` are accepted by the import and then reported by [Pre-flight](../tabs/preflight.md) as `invalid_constraint`. See [Pre-flight issues](preflight-issues.md).

## Rooms and activities

| Message | Cause | Fix |
|---|---|---|
| `Activities!R2C7 [room_type]: required unless room_count is 0 (or the activity is online)` | An in-person activity has no room type | Give it a `room_type`, set `room_count` to 0, or set `delivery` to `online` |
| `Activities!R2C8 [room_count]: expected integer ≥ 1 when room_type is set` | A room type with a `room_count` of 0 | Use 1 or more, or clear `room_type` |
| `Activities!R2C7 [room_type]: an online activity cannot have a room type` | `delivery` is `online` and a room is asked for | Clear `room_type`, or make it `in_person` |
| `Activities!R2C8 [room_count]: an online activity cannot have rooms` | Same, for `room_count` | Clear `room_count`, or make it `in_person` |

## Templates

| Message | Cause | Fix |
|---|---|---|
| `Templates!R2C6 [batch_size]: required when mode is "batched"` | Mode `batched` without a batch size | Fill in `batch_size` |
| `Templates!R2C5 [groups]: under: needs a value` | The `groups` selector is not valid | See [Selectors](../constraints/selectors.md) |

A template that cannot be expanded (for example a selector that matches no group) is reported here too, as an error on the `Templates` sheet, because template rows are expanded once when a version 1 file is imported.

## Configuration (format version 2)

These come from a version 2 file, or from editing the Session types, Modules, Teachers and Groups tables of a dataset built from configuration. The row and column point at the cell to fix.

| Message | Cause | Fix |
|---|---|---|
| `Modules!R2C6 [sessions]: unknown code "XYZ"` | A module lists a session type that is not in the Session types table | Add the session type, or correct the code |
| `Modules!R2C6 [sessions]: cannot read "LEC(max_groups)": expected name=value` | A setting in brackets has no value | Write `name=value`, for example `LEC(max_groups=2)` |
| `Modules!R2C6 [sessions]: unknown setting "size" (known: start_pattern, delivery, room_type, max_groups, teachers, weekly)` | A setting that does not exist | Use one of the six settings named in the message |
| `Modules!R2C6 [sessions]: cannot read "LEC(max_groups=0)": max_groups must be an integer ≥ 1` | A setting with a value that is not allowed. `weekly` must also be 1 or more, and `teachers` 0 or more | Use a whole number in range |
| `Modules!R2C6 [sessions]: cannot read "LEC(delivery=hybrid)": delivery must be in_person or online` | A delivery that is not one of the two | Use `in_person` or `online` |
| `Modules!R2C6 [sessions]: cannot read "LEC(start_pattern=9H)": unknown start pattern "9H"` | The start pattern is not in the Start patterns table | Use a code from [StartPatterns](../tables/StartPatterns.md) |
| `Modules!R2C3 [level]: required` | A module has no level. A module belongs to exactly one | Fill in `level` |
| `Teachers!R2C3 [modules]: unknown code "NOPE"` | A teacher lists a module that does not exist | Correct the code |
| `Teachers!R2C3 [modules]: "6BUIS019C:LAB": module "6BUIS019C" has no session type "LAB"` | A teacher is limited to a kind of session the module does not have | Add the kind to the module's `sessions`, or correct the kind |
| `Groups!R2C5 [options]: module "6COSC020C" is not optional` | A group lists a mandatory module as an option. Every group of the programme takes a mandatory module anyway | Remove it from `options`, or tick `optional` on the module |
| `Groups!R2C5 [options]: unknown code "NOPE"` | A group lists a module that does not exist | Correct the code |
| `Groups!R2C3 [parent]: unknown code "L6 CS / G10"` | A group's parent is another group. In version 2 a group belongs to a programme | Give the programme's code |
| `SessionTypes!R2C5 [room_type]: an online session cannot have a room type` | An online session type asks for a room type | Clear `room_type`, or make it `in_person` |
| `SessionTypes!R2C5 [room_type]: required when delivery is "in_person"` | An in-person session type has no room type | Fill in `room_type`, or make it `online` |
| `SessionTypes!R2C6 [max_groups]: expected integer ≥ 1, got "0"` | Zero groups per session | Use 1 or more, or leave it blank for all the groups in one session |
| `Activities: unknown sheet` | A version 2 file has an Activities sheet. So do `Templates`, `ActivityGroups`, `ActivityTeachers` and `Pins` | Remove the sheet: the solver makes the sessions. To keep typed activities use a version 1 file |

## Assignments (a result workbook)

| Message | Cause | Fix |
|---|---|---|
| `Assignments: contains several runs (run-99, seed-0)` | The `run` column holds more than one run name | Keep one run's rows |
| `Assignments!R2C6 [start]: no period starts at 08:45` | The start time is not exactly the start of a period | Use a period's start time |

## Messages from the table editor

When you add, change or delete a single row, the same checks run on the whole dataset, so you see the messages above, headed by **the change is not valid**. A few more come from the editor itself:

| Message | Cause | Fix |
|---|---|---|
| `a row with key "AB" already exists in Teachers` | You added a row whose code is already used | Use a different code, or edit the existing row |
| `no row "AB" in Teachers` | The row was deleted or renamed in the meantime | Reload the table |
| `unknown column "…"` | A column the table does not have | Use the columns shown |
| `no table "…" in preset academic_weekly` | The table name in the address is wrong | Use the tab names |

A refused **delete** lists the rows that still refer to the row you tried to delete, as `unknown code` messages. Delete or correct those first.

## Related

- [Import / export](../tabs/import-export.md)
- [Basics](../basics.md)
- [Pre-flight issues](preflight-issues.md)
