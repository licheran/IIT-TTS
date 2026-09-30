# Availability

Sheet name in Excel and CSV files: `Availability`.

## What it is

When a resource (a teacher, a room, a group) **cannot** be used, or had better not be.

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `resource` | The code of any resource: a teacher, room, group and so on. | text | yes | — | a code from [Universities](Universities.md), [Levels](Levels.md), [Programmes](Programmes.md), [Groups](Groups.md), [Teachers](Teachers.md), [Campuses](Campuses.md), [Buildings](Buildings.md), [Rooms](Rooms.md) |
| `day` | The day. | text | yes | — | a code from [Days](Days.md) |
| `period` | The period, or `*` for the whole day. | text | yes | — | a code from [Periods](Periods.md); or `*` for every period of the day |
| `status` | `unavailable` is a rule that always holds. `avoid` is a preference. | text | yes | — | one of `unavailable`, `avoid` |

## Rules

- **`unavailable`** is always obeyed: no activity is placed on that resource in that slot. Because breaks cannot be used anyway, `unavailable` rows on breaks have no effect.
- **`avoid`** only has effect if the Constraints table also has a constraint of type `avoid` whose `scope` covers the resource. Without one, `avoid` rows are kept and ignored. See the [`avoid`](../constraints/avoid.md) constraint.
- `period` `*` marks every period of the day.
- Setting a teacher unavailable for too many periods makes pre-flight report `over_demand`.

## Example

An illustration (the L6 sample workbook has no rows in this table):

| `resource` | `day` | `period` | `status` |
|---|---|---|---|
| HAWE | Mon | * | unavailable |
| [2LA] -GP | Fri | P08 | avoid |

## Related

- [All tables](README.md)
- [Basics](../basics.md)
- [Import and editing errors](../troubleshooting/import-errors.md): what each message means and how to fix it
