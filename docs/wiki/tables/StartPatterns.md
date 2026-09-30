# Start patterns

Sheet name in Excel and CSV files: `StartPatterns`.

## What it is

Tells the solver **when an activity of a given length may start**. Each activity names one pattern.

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `code` | A name that activities refer to, for example `2H` for two-hour activities. | text | yes | — | — |
| `duration` | How many consecutive periods an activity with this pattern lasts. | whole number ≥ 1 | yes | — | — |
| `start_periods` | The periods an activity may start in. | list | yes | — | codes from [Periods](Periods.md) |
| `days` | The days it may be placed on. Leave blank for every day. | list | no | — | codes from [Days](Days.md) |

## Rules

- An activity's own `duration` should match the pattern's `duration`.
- Pick only starts where the whole activity fits in one day without touching a break. In the sample the pattern `2H` lasts 2 periods and starts at `P01;P03;P06;P08;P10`: it never spans the break `P05`.
- If no start fits, pre-flight reports `empty_start_domain` for each activity that uses the pattern.

## Example

From the L6 sample:

| `code` | `duration` | `start_periods` | `days` |
|---|---|---|---|
| 2H | 2 | P01;P03;P06;P08;P10 |   |

## Related

- [All tables](README.md)
- [Basics](../basics.md)
