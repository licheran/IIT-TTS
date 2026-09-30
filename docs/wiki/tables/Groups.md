# Groups

Sheet name in Excel and CSV files: `Groups`.

## What it is

The student groups: the cohorts that attend activities together. **A group is an exclusive resource: it can be in only one activity at a time.** This is the table you fill in most for the academic preset.

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `code` | The unique name of this row. Other tables refer to it. | text | yes | — | — |
| `name` | A longer name for people. Free text. It is not used for matching. | text | no | — | — |
| `parent` | The programme the group belongs to, or another group when it is a sub-group. | text | yes | — | a code from [Programmes](Programmes.md), [Groups](Groups.md) |
| `size` | How many students. Used to choose rooms that are big enough. | whole number ≥ 0 | no | — | — |
| `tags` | Labels of the form `key=value`, separated by `;`. See the Tags page. | key=value pairs | no | — | — |

Tags are explained on the [Tags](tags.md) page.

## Rules

- **`parent` is required.** It may name a programme or another group (a subgroup such as `L6 SE / G1a`).
- An activity for a group occupies the group and all of its sub-groups. An activity for a sub-group does **not** occupy the parent group.
- When an activity serves several groups, a room must seat the **sum of their sizes**.
- Realistic sizes are 20 to 60, but any whole number is allowed.

## Example

From the L6 sample:

| `code` | `name` | `parent` | `size` | `tags` |
|---|---|---|---|---|
| L6 CS / G1 | L6 CS / G1 | L6 CS | 30 |   |
| L6 CS / G10 | L6 CS / G10 | L6 CS | 30 |   |

## Related

- [All tables](README.md)
- [Basics](../basics.md)
