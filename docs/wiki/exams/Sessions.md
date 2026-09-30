# Sessions

Sheet name in Excel and CSV files: `Sessions`.

## What it is

The exam slots of a day, for example a morning and an afternoon session. This is the same table as **Periods** in the academic preset, with a different name.

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `code` | A short name, for example `AM`. | text | yes | — | — |
| `start` | When the session starts, `HH:MM`. | time (HH:MM) | yes | — | — |
| `end` | When it ends. | time (HH:MM) | yes | — | — |
| `order` | The position in the day: 1 is the first session. | whole number | yes | — | — |
| `is_break` | True for a slot nothing may be scheduled in. | true/false | no | false | — |

## Rules

- In the sample there are two sessions: `AM` 09:00 to 12:00 and `PM` 14:00 to 17:00. An exam takes one whole session.
- An exam can never cover a break, just as in the academic preset.

## Example

From the exams sample (`backend/tests/fixtures/exams/exams.xlsx`):

| `code` | `start` | `end` | `order` | `is_break` |
|---|---|---|---|---|
| AM | 09:00 | 12:00 | 1 | false |
| PM | 14:00 | 17:00 | 2 | false |

## Related

- [The exams preset](README.md)
- [Basics](../basics.md)
- [Import and editing errors](../troubleshooting/import-errors.md)
