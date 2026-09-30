# Constraints

## What they are

A **constraint** is a rule about the timetable. Some rules always hold and you never write them. Others are yours: you add a row to the [Constraints](../tables/Constraints.md) table, choose a **type** from a fixed list of fourteen, say **whom or what it covers** with a selector, and decide whether it is **hard** or **soft**.

## Rules that always hold

These are built in. You cannot switch them off, and a timetable that breaks one is never produced.

| Rule | In plain words |
|---|---|
| Placement | Every activity gets exactly one start, in a slot its start pattern allows, and the rooms it needs |
| No double booking | A group, a teacher or a room is in at most one activity at a time. An activity for a whole programme occupies every group below it |
| Unavailable | Nothing is placed on a resource in a slot its Availability table marks `unavailable` |
| Capacity | A chosen room seats at least the sum of the sizes of the groups attending |
| Room match | A chosen room is of the type the activity asked for |
| Pins | An activity with a pin is exactly where the pin says |

## Your rules: hard and soft

Each row of the Constraints table is one of these:

- **Hard** (`hard` true). The rule **must** hold. If the hard rules cannot all hold together, no timetable exists: the run ends `infeasible` and names the conflicting rules.
- **Soft** (`hard` false). The rule is a **preference**. Every time it is broken it adds to a **score**, and the solver looks for the timetable with the lowest score. A timetable that breaks soft rules is still valid.

The columns of the table are explained on the [Constraints table](../tables/Constraints.md) page. In short: `code` (your name for it), `type`, `scope`, `params`, `hard`, `weight`, `active`.

### The score

Each soft rule counts a **penalty** (a whole number saying how badly it is broken, explained on each type's page). The score is

```
score = sum over all soft rules of  weight × penalty
```

`0` means every preference is met. Lower is better. The **weight** says how much you mind: a rule with weight 5 counts five times as much as one with weight 1 for the same amount of breaking. Only the relative sizes matter. The weight of a hard rule is ignored.

After a run, the Run tab shows a **Score breakdown**: one line for each soft rule, with its penalty, weight and score, largest first. Read it from the top: the first line is the rule costing you most.

### Choosing hard or soft

- Use **hard** for what is truly impossible to accept, such as a teacher's contract limit.
- Use **soft** for what you would like, such as few gaps. Soft rules never make a run fail.
- If a run is `infeasible`, changing a hard rule to soft is the quickest way to see what the timetable would look like without it.

## The fourteen types

| Type | Covers | What it asks for |
|---|---|---|
| [`max_per_day`](max_per_day.md) | resources | At most so many periods (or activities) a day |
| [`max_gaps`](max_gaps.md) | resources | At most so many free periods inside a day |
| [`max_days`](max_days.md) | resources | Busy on at most so many days a week |
| [`min_days_between`](min_days_between.md) | activities | Any two are so many days apart |
| [`same_start`](same_start.md) | activities | All start at the same day and period |
| [`same_day`](same_day.md) | activities | All on the same day |
| [`order`](order.md) | activities | A sequence happens in order |
| [`consecutive`](consecutive.md) | activities | A sequence runs back to back |
| [`not_overlapping`](not_overlapping.md) | activities | No two share a period |
| [`travel_gap`](travel_gap.md) | resources | Free time to change building |
| [`preferred_times`](preferred_times.md) | activities | Start in one of a list of slots |
| [`preferred_resources`](preferred_resources.md) | activities | Use rooms that match a selector |
| [`avoid`](avoid.md) | resources | Keep out of the slots marked `avoid` in Availability |
| [`max_span`](max_span.md) | resources | The day is no longer than so many periods |

The list is fixed. A type that is not on it is refused when you import or edit the table.

"Covers resources" means the `scope` selects groups, teachers, rooms and so on, and the rule applies to **each one separately** (the penalties add up). "Covers activities" means the `scope` selects activities, and the rule applies to the selected activities **together**.

## Scope

The `scope` column is a **selector**. Write `type:Teacher` to cover every teacher, `kind:TUT` to cover every tutorial. The [Selectors](selectors.md) page explains every clause, with examples.

## Defaults

A new academic dataset starts with a few preferences already in the table, and the exams preset adds one rule per cohort. They are listed on the [Default constraints](defaults.md) page.

## Related

- [Selectors](selectors.md)
- [Default constraints](defaults.md)
- [The Constraints table](../tables/Constraints.md)
- [Run](../tabs/run.md) (the score breakdown)
