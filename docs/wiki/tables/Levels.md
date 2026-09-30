# Levels

Sheet name in Excel and CSV files: `Levels`.

## What it is

The academic levels, for example `L6`. A level belongs to a university (optional) and contains programmes.

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `code` | The unique name of this row. Other tables refer to it. | text | yes | — | — |
| `name` | A longer name for people. Free text. It is not used for matching. | text | no | — | — |
| `university` | The university this level belongs to. Optional. | text | no | — | a code from [Universities](Universities.md) |
| `tags` | Labels of the form `key=value`, separated by `;`. See the Tags page. | key=value pairs | no | — | — |

Tags are explained on the [Tags](tags.md) page.

## Rules

- A level only groups programmes. It is not scheduled.
- Different levels may teach on different days or in blocks of different lengths. Give each level's activities the start pattern that fits it: a start pattern can be limited to certain days.

## Example

From the L6 sample:

| `code` | `name` | `university` | `tags` |
|---|---|---|---|
| L6 | L6 |   |   |

## Related

- [All tables](README.md)
- [Basics](../basics.md)
- [Import and editing errors](../troubleshooting/import-errors.md): what each message means and how to fix it
