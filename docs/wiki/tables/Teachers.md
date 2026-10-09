# Teachers

Sheet name in Excel and CSV files: `Teachers`.

## What it is

The teachers. **A teacher is an exclusive resource: they can teach only one activity at a time.**

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `code` | The unique name of this row. Other tables refer to it. | text | yes | — | — |
| `name` | A longer name for people. Free text. It is not used for matching. | text | no | — | — |
| `modules` | The modules the teacher may teach, separated by `;`. Write `module:KIND` to teach only that kind of session. | list | no | — | codes from [Modules](Modules.md), or `module:KIND`; stored as an attribute |
| `max_hours` | The most periods the teacher may be occupied in a week. Leave blank for no limit. One period is one hour in the L6 data. | whole number ≥ 0 | no | — | stored as an attribute |
| `tags` | Labels of the form `key=value`, separated by `;`. See the Tags page. | key=value pairs | no | — | — |

Tags are explained on the [Tags](tags.md) page.

## Rules

- Each code refers to exactly one teacher. Use one code per person.
- **The solver chooses the teacher** of each session from the teachers who list its module. `6SENG005C` means every kind of session of that module; `6SENG005C:TUT` means tutorials only.
- **`max_hours` is a hard limit.** The solver never gives a teacher more than this many periods in a week (the program makes a [`max_load`](../constraints/max_load.md) rule for them). If the limits make a timetable impossible, the run ends `infeasible`. Leave it blank for no limit.
- The load of a module's teachers is also shared out evenly, as far as possible, and a group keeps one teacher for a module's sessions of one kind: see [Default constraints](../constraints/defaults.md).
- A module nobody lists has no teacher, and its sessions cannot be scheduled (pre-flight says so).
- In a hand-made dataset (format version 1) a teacher is attached to an activity in the ActivityTeachers table, and there is no `modules` or `max_hours` column.
- To say when a teacher is not available, use the Availability table.

## Example

A small example:

| `code` | `name` | `modules` | `max_hours` | `tags` |
|---|---|---|---|---|
| HAWE | Dr Hawe | 6SENG005C | 18 | |
| HARR | Dr Harr | 6SENG005C:TUT;6SENG012C | | |

## Related

- [All tables](README.md)
- [Basics](../basics.md)
- [Import and editing errors](../troubleshooting/import-errors.md): what each message means and how to fix it
