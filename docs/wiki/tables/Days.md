# Days

Sheet name in Excel and CSV files: `Days`.

## What it is

The days of the timetable week, left to right. Fill it in before anything else: no activity can be placed until the dataset has days.

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `code` | A short name used by other tables, for example `Mon`. | text | yes | — | — |
| `label` | The name shown in grids. If blank, the code is shown. | text | no | — | — |
| `order` | The position of the day in the week: 1 is the first column. Days are shown in this order. | whole number | yes | — | — |

## Rules

- The days are any days you want to schedule on. The sample has `Mon` to `Sat`.
- An exam session uses dates as day codes instead (see the exams preset).

## Example

From the L6 sample:

| `code` | `label` | `order` |
|---|---|---|
| Mon | Monday | 1 |
| Tue | Tuesday | 2 |

## Related

- [All tables](README.md)
- [Basics](../basics.md)
- [Import and editing errors](../troubleshooting/import-errors.md): what each message means and how to fix it
