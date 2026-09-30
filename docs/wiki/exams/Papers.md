# Papers

Sheet name in Excel and CSV files: `Papers`.

## What it is

The exam papers, for example one for each module. A paper is **not scheduled itself**: it is a label that an exam points to, and its code is shown on the timetable.

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `code` | The paper's unique code, for example `CS101`. | text | yes | — | — |
| `name` | The title. Free text. | text | no | — | — |
| `minutes` | How long the paper lasts in minutes. For information: the time an exam takes on the timetable is its session. | whole number ≥ 0 | no | — | stored as an attribute |
| `tags` | Labels of the form `key=value`, separated by `;`. See [Tags](../tables/tags.md). | key=value pairs | no | — | — |

## Rules

- An exam names its paper in its `paper` column. A selector can pick an exam by its paper with `ref:<code>`.
- `minutes` is kept with the paper and is not used by any rule today.

## Example

From the exams sample (`backend/tests/fixtures/exams/exams.xlsx`):

| `code` | `name` | `minutes` | `tags` |
|---|---|---|---|
| AI501 |   | 180 |   |
| AI502 |   | 120 |   |

## Related

- [The exams preset](README.md)
- [Basics](../basics.md)
- [Import and editing errors](../troubleshooting/import-errors.md)
