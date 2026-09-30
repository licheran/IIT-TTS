# Campuses

Sheet name in Excel and CSV files: `Campuses`.

## What it is

The campuses. A building belongs to a campus. Keep a single campus if you do not need the distinction.

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `code` | The unique name of this row. Other tables refer to it. | text | yes | — | — |
| `name` | A longer name for people. Free text. It is not used for matching. | text | no | — | — |
| `tags` | Labels of the form `key=value`, separated by `;`. See the Tags page. | key=value pairs | no | — | — |

Tags are explained on the [Tags](tags.md) page.

## Rules

- A campus only groups buildings. Nothing is scheduled on it.

## Example

From the L6 sample:

| `code` | `name` | `tags` |
|---|---|---|
| MAIN | MAIN |   |

## Related

- [All tables](README.md)
- [Basics](../basics.md)
- [Import and editing errors](../troubleshooting/import-errors.md): what each message means and how to fix it
