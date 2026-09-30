# Modules

Sheet name in Excel and CSV files: `Modules`.

## What it is

The modules (courses) that activities belong to. A module is **not scheduled itself**: it is a label that gives activities a name to show and to select on. Its code appears in bold on the timetable blocks.

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `code` | The module's unique code, for example `6SENG005C`. | text | yes | — | — |
| `name` | The module's title. Free text. | text | no | — | — |
| `level` | The level the module is taught at. For information. | text | no | — | a code from [Levels](Levels.md); stored as an attribute |
| `programme` | The programme it belongs to. For information. | text | no | — | a code from [Programmes](Programmes.md); stored as an attribute |
| `tags` | Labels of the form `key=value`, separated by `;`. See the Tags page. | key=value pairs | no | — | — |

Tags are explained on the [Tags](tags.md) page.

## Rules

- An activity names its module in its `module` column. Selectors can pick an activity's module with `ref:<code>`.
- `level` and `programme` are kept with the module, and are not used by any rule today.

## Example

From the L6 sample:

| `code` | `name` | `level` | `programme` | `tags` |
|---|---|---|---|---|
| 6BUIS019C | 6BUIS019C |   |   |   |
| 6CCGD007C | 6CCGD007C |   |   |   |

## Related

- [All tables](README.md)
- [Basics](../basics.md)
- [Import and editing errors](../troubleshooting/import-errors.md): what each message means and how to fix it
