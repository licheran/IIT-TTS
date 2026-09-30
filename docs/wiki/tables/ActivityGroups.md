# Activity groups

Sheet name in Excel and CSV files: `ActivityGroups`.

## What it is

Says **which groups attend which activity**: one row per pair. An activity with several rows is a joint activity.

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `activity` | The activity. | text | yes | — | a code from [Activities](Activities.md) |
| `group` | The group, programme or level that attends. A programme or level means all the groups below it. | text | yes | — | a code from [Groups](Groups.md), [Programmes](Programmes.md), [Levels](Levels.md) |

## Rules

- Naming a programme or level is shorthand for every exclusive group below it. The activity occupies all of them.
- To add a group to an activity, add a row. To remove it, delete the row.

## Example

From the L6 sample:

| `activity` | `group` |
|---|---|
| 6BUIS019C-LEC-01 | L6 CS / G12 |
| 6BUIS019C-LEC-01 | L6 CS / G13 |

## Related

- [All tables](README.md)
- [Basics](../basics.md)
- [Import and editing errors](../troubleshooting/import-errors.md): what each message means and how to fix it
