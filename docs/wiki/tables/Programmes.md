# Programmes

Sheet name in Excel and CSV files: `Programmes`.

## What it is

The degree programmes, for example `L6 SE`. A programme belongs to a level and contains groups.

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `code` | The unique name of this row. Other tables refer to it. | text | yes | — | — |
| `name` | A longer name for people. Free text. It is not used for matching. | text | no | — | — |
| `level` | The level this programme belongs to. Optional. | text | no | — | a code from [Levels](Levels.md) |
| `tags` | Labels of the form `key=value`, separated by `;`. See the Tags page. | key=value pairs | no | — | — |

Tags are explained on the [Tags](tags.md) page.

## Rules

- An activity may name a whole programme as attending. It then occupies every group below it.

## Example

From the L6 sample:

| `code` | `name` | `level` | `tags` |
|---|---|---|---|
| L6 CS | L6 CS | L6 |   |
| L6 SE | L6 SE | L6 |   |

## Related

- [All tables](README.md)
- [Basics](../basics.md)
