# Invigilators

Sheet name in Excel and CSV files: `Invigilators`.

## What it is

The staff who supervise exams. **An invigilator is an exclusive resource: one exam at a time.**

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `code` | The unique code of the invigilator. | text | yes | — | — |
| `name` | A longer name. Free text. | text | no | — | — |
| `tags` | Labels of the form `key=value`, separated by `;`. See [Tags](../tables/tags.md). | key=value pairs | no | — | — |

## Rules

- Each exam needs a number of invigilators, set in the `invigilators` column of [Exams](Exams.md). The program chooses who.
- To say when an invigilator is away, use [Availability](../tables/Availability.md).

## Example

From the exams sample (`backend/tests/fixtures/exams/exams.xlsx`):

| `code` | `name` | `tags` |
|---|---|---|
| INV01 |   |   |
| INV02 |   |   |

## Related

- [The exams preset](README.md)
- [Basics](../basics.md)
- [Import and editing errors](../troubleshooting/import-errors.md)
