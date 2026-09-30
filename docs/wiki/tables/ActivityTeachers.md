# Activity teachers

Sheet name in Excel and CSV files: `ActivityTeachers`.

> **Hand-made datasets only.** This sheet is part of format version 1 files. The application shows no table for it: a hand-made dataset's teachers appear as the `teachers` column of [Activities](Activities.md), where you edit them. In a dataset built from configuration, teachers list the modules they teach (see [Teachers](Teachers.md)) and the solver chooses who takes each session.

## What it is

Says **which teachers teach which activity**: one row per pair.

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `activity` | The activity. | text | yes | — | a code from [Activities](Activities.md) |
| `teacher` | The teacher. | text | yes | — | a code from [Teachers](Teachers.md) |

## Rules

- A teacher can teach only one activity at a time, so two activities that share a teacher never overlap.
- An activity may have several teachers. It then occupies all of them.
- An activity with no teacher row is allowed.

## Example

From the L6 sample:

| `activity` | `teacher` |
|---|---|
| 6BUIS019C-LEC-01 | THE |
| 6BUIS019C-TUT-01 | IMAS |

## Related

- [All tables](README.md)
- [Basics](../basics.md)
- [Import and editing errors](../troubleshooting/import-errors.md): what each message means and how to fix it
