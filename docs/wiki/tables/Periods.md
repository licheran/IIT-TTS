# Periods

Sheet name in Excel and CSV files: `Periods`.

## What it is

The time slots of a day, top to bottom. Every day has the same periods. An activity lasts a whole number of consecutive periods.

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `code` | A short name, for example `P01`. | text | yes | — | — |
| `start` | When the period starts, `HH:MM` on the 24-hour clock. | time (HH:MM) | yes | — | — |
| `end` | When it ends. | time (HH:MM) | yes | — | — |
| `order` | The position in the day: 1 is the top row. | whole number | yes | — | — |
| `is_break` | True for a period nothing may be scheduled in, such as lunch. | true/false | no | false | — |

## Rules

- **An activity can never cover a break.** A two-period activity that would start just before a break has no valid start there. Choose start patterns that avoid it (see Start patterns).
- Break periods are drawn in grey in the timetable.
- In the sample, `P05` (12:30 to 13:30) is the lunch break.

## Example

From the L6 sample:

| `code` | `start` | `end` | `order` | `is_break` |
|---|---|---|---|---|
| P01 | 08:30 | 09:30 | 1 | false |
| P02 | 09:30 | 10:30 | 2 | false |

## Related

- [All tables](README.md)
- [Basics](../basics.md)
