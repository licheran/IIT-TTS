# Halls

Sheet name in Excel and CSV files: `Halls`.

## What it is

The rooms exams are held in. **A hall is an exclusive resource: one exam at a time.** The program chooses the hall; you only say how many it seats.

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `code` | The unique code of the hall. | text | yes | — | — |
| `name` | A longer name. Free text. | text | no | — | — |
| `capacity` | How many candidates the hall seats. | whole number ≥ 0 | no | — | — |
| `tags` | Labels of the form `key=value`, separated by `;`. See [Tags](../tables/tags.md). | key=value pairs | no | — | — |

## Rules

- Each exam gets **exactly one hall**, any hall that seats all its candidates. There is no hall type.
- The **largest hall is a hard limit**: an exam with more candidates than any hall seats cannot be placed, and pre-flight says so (`no_candidate`).

## Example

From the exams sample (`backend/tests/fixtures/exams/exams.xlsx`):

| `code` | `name` | `capacity` | `tags` |
|---|---|---|---|
| EXAM-ROOM |   | 60 |   |
| HALL-B |   | 160 |   |

## Related

- [The exams preset](README.md)
- [Basics](../basics.md)
- [Import and editing errors](../troubleshooting/import-errors.md)
