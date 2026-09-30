# Universities

Sheet name in Excel and CSV files: `Universities`.

## What it is

The awarding universities, when the institute teaches programmes for several. A level can belong to a university. Leave the table empty if you do not need this.

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `code` | The unique name of this row. Other tables refer to it. | text | yes | — | — |
| `name` | A longer name for people. Free text. It is not used for matching. | text | no | — | — |
| `tags` | Labels of the form `key=value`, separated by `;`. See the Tags page. | key=value pairs | no | — | — |

Tags are explained on the [Tags](tags.md) page.

## Rules

- A university only groups levels. It is not scheduled and nothing is booked on it.
- Its main use is in selectors, for example `under:UOW` picks every group below it.

## Example

This table is empty in the L6 sample.

## Related

- [All tables](README.md)
- [Basics](../basics.md)
