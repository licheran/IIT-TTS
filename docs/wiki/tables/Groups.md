# Groups

Sheet name in Excel and CSV files: `Groups`.

## What it is

The student groups: the cohorts that attend activities together. **A group is an exclusive resource: it can be in only one activity at a time.** This is the table you fill in most for the academic preset.

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `code` | The unique name of this row. Other tables refer to it. | text | yes | — | — |
| `name` | A longer name for people. Free text. It is not used for matching. | text | no | — | — |
| `parent` | The programme the group belongs to. | text | yes | — | a code from [Programmes](Programmes.md) |
| `size` | How many students. Used to choose rooms that are big enough. | whole number ≥ 0 | no | — | — |
| `options` | The optional modules this group takes, separated by `;`. | list | no | — | codes from [Modules](Modules.md); stored as an attribute |
| `tags` | Labels of the form `key=value`, separated by `;`. See the Tags page. | key=value pairs | no | — | — |

Tags are explained on the [Tags](tags.md) page.

## Rules

- **`parent` is required and must be a programme.** A group cannot be the parent of another group (`unknown code`).
- **A group is students who share the same optional modules.** The group takes every mandatory module of its programme, and the optional modules it lists in `options`. Each option must be an optional module at the group's level that is offered to its programme.
- When an activity serves several groups, a room must seat the **sum of their sizes**.
- Realistic sizes are 20 to 60, but any whole number is allowed.
- In a hand-made dataset (format version 1) a group may be the child of another group (a sub-group), and there is no `options` column.

## Example

| `code` | `name` | `parent` | `size` | `options` | `tags` |
|---|---|---|---|---|---|
| L6 SE / G1 | L6 SE / G1 | L6 SE | 30 | 6SENG012C |   |
| L6 SE / G2 | L6 SE / G2 | L6 SE | 30 |   |   |

## Related

- [All tables](README.md)
- [Basics](../basics.md)
- [Import and editing errors](../troubleshooting/import-errors.md): what each message means and how to fix it
