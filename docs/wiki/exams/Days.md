# Exam days

Sheet name in Excel and CSV files: `Days`.

## What it is

The days of the exam session. In the academic preset days are weekdays such as `Mon`. Here **each day is a date**, so the session can run over several weeks without repeating names.

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `code` | The date, written `YYYY-MM-DD`, for example `2026-06-01`. Other tables refer to it. | text | yes | — | — |
| `label` | The text shown in grids, for example `Mon 01 Jun`. | text | no | — | — |
| `order` | The position in the session: 1 is the first day. List the days in date order. | whole number | yes | — | — |

## Rules

- Add only the days exams may be held on. Leave out weekends and holidays: a day that is not here is never used.
- The code is just a name to the program, so any unique text works, but the date form keeps exports easy to read.
- The sample has ten weekdays over two weeks, starting on Monday 1 June 2026.

## Example

From the exams sample (`backend/tests/fixtures/exams/exams.xlsx`):

| `code` | `label` | `order` |
|---|---|---|
| 2026-06-01 | Mon 01 Jun | 1 |
| 2026-06-02 | Tue 02 Jun | 2 |

## Related

- [The exams preset](README.md)
- [Basics](../basics.md)
- [Import and editing errors](../troubleshooting/import-errors.md)
