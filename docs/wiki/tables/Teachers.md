# Teachers

Sheet name in Excel and CSV files: `Teachers`.

## What it is

The teachers. **A teacher is an exclusive resource: they can teach only one activity at a time.**

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `code` | The unique name of this row. Other tables refer to it. | text | yes | — | — |
| `name` | A longer name for people. Free text. It is not used for matching. | text | no | — | — |
| `tags` | Labels of the form `key=value`, separated by `;`. See the Tags page. | key=value pairs | no | — | — |

Tags are explained on the [Tags](tags.md) page.

## Rules

- Each code refers to exactly one teacher. Use one code per person.
- A teacher is attached to an activity in the ActivityTeachers table, or in the `teachers` column of a template.
- To say when a teacher is not available, use the Availability table.

## Example

From the L6 sample:

| `code` | `name` | `tags` |
|---|---|---|
| AAM | AAM |   |
| ABM | ABM |   |

## Related

- [All tables](README.md)
- [Basics](../basics.md)
- [Import and editing errors](../troubleshooting/import-errors.md): what each message means and how to fix it
