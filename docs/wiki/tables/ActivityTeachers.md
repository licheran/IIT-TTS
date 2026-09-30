# Activity teachers

Sheet name in Excel and CSV files: `ActivityTeachers`.

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
