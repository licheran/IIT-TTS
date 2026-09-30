# Infeasible runs

## What it's for

A run is **infeasible** when no timetable can satisfy all the hard rules at once, however long the solver searches. The solver does not give up: it has proved that it is impossible. What you need to know is **which rules** collide, and this page shows how to read that and what to change.

## How to read the explanation

Under **Why it did not finish**, an infeasible run shows one sentence beginning `Conflicting rules:` followed by the rules that cannot hold together. Each rule is separated by `;`. The explanation is the **smallest set** the program could find: take away any one of them and a timetable would exist (unless it adds `may include rules that are not needed`).

For example:

```
Conflicting rules: Teacher THE unavailable Mon P01; pin of 6BUIS019C-LEC-01 to Mon P01
```

reads: "the teacher THE is unavailable on Monday in `P01`, and the activity `6BUIS019C-LEC-01`, which THE teaches, is pinned to Monday `P01`". Remove either and the conflict goes away.

The phrases you may meet:

| Phrase | Means | Where to change it |
|---|---|---|
| `Teacher THE unavailable Mon P01` | Availability rows mark the resource unavailable. Days that repeat are written as a range: `Tue–Sat`. Periods as `P01–P03, P05`. A whole day has no periods after it | [Availability](../tables/Availability.md) |
| `8 events of 2 periods for HAWE` | The resource is needed by 8 activities of 2 periods each. When lengths differ it reads `8 events, 20 periods in all, for HAWE` | [Activities](../tables/Activities.md), [ActivityTeachers](../tables/ActivityTeachers.md), [ActivityGroups](../tables/ActivityGroups.md) |
| `no_overlap(HAWE)` | The resource can only do one thing at a time, which is what makes the load above a problem | (always on) |
| `constraint C-MAXDAYS (max_days)` | One of your hard constraints is part of the conflict | [Constraints](../tables/Constraints.md) |
| `pin of 6BUIS019C-LEC-01 to Mon P01` | A pin is part of the conflict. It names the day, period and rooms pinned | [Pins](../tables/Pins.md), or unpin on the [Timetable](../tabs/timetable.md) tab |
| `6BUIS019C-TUT-03 has no allowed start for duration 2` | No start of the activity's pattern fits | [Start patterns](../tables/StartPatterns.md) |
| `6COSC023C-LEC-01 needs 1 Room matching "tag:room_type=lab"` | The activity's room requirement is part of the conflict | [Rooms](../tables/Rooms.md) |
| `the time grid and durations alone leave no solution` | Nothing specific was found: the days, periods and durations cannot fit the activities | [Days](../tables/Days.md), [Periods](../tables/Periods.md) |

The entries are in this order: your constraints first, then availability, pins, starts, requirements and loads, so the things you most likely want to change come first.

## How to fix it

Work from the explanation:

1. **Remove or relax one rule** of the conflict.
   - A hard constraint: make it soft (set `hard` to false and give it a weight), or loosen its `params`.
   - A pin: unpin it.
   - An availability row: delete it, or shorten the period.
2. **Add capacity** where the load is the problem.
   - More rooms of the needed type, more start patterns, or more days and periods.
   - Less work for the resource: move some of its activities to another teacher or room.
3. **Run again.** A new run uses the current data.

If you change several things at once you will not know which one helped. Change one, run, repeat.

## When the explanation is missing or long

- **`No timetable can satisfy every hard rule, but the conflicting rules could not be found in the time available.`** The solver proved there is no timetable, but finding the smallest conflicting set takes more time than the program allows (5 seconds for the first proof, 60 in all). The data is usually large or tightly packed. Try making a few hard constraints soft, one at a time, starting with the most restrictive, and run again.
- **`(may include rules that are not needed: the search ran out of time)`** The conflict is real but may list extra rules. Remove the rules you can do without, one at a time.
- **An explanation that names a lot of rules** usually means the week is simply too full for one resource. Look for `… events … for <resource>` and reduce its load.

## Common causes

| Symptom | Likely cause |
|---|---|
| A teacher's name appears with many events and an availability range | The teacher has more hours than the days they are available |
| A room type appears in a `needs … Room matching` sentence | Too few rooms of that type, or the capacity needed is more than any of them seats |
| A `constraint` appears with `max_days`, `max_per_day` or `max_gaps` | The hard limit is lower than the work needs. Make it soft |
| A `pin` appears | The pin clashes with something. Unpin it |
| Two activities of the same group or teacher are each pinned at one time | They were pinned to overlap. This is reported earlier as `conflicting_pins` by pre-flight |

## Frequently asked

**The run is slow.** The solver uses the whole time limit to improve the score when there are soft rules. Lower the time limit, or use the mode `feasible` to stop at the first valid timetable. A dataset of several thousand activities can take a minute or more.

**The score is not 0.** Not every preference can always be met. Open the score breakdown on the Run tab and look at the first line: it is the rule costing the most. See [Constraints](../constraints/README.md).

**Two datasets clash.** Teachers or rooms shared between two datasets can be double-booked across them. Publish one dataset's run and start the other with **Lock published runs** ticked, and it keeps away from the published times. To check for clashes, the command `tts clashes` compares the timetables of several workbooks, and the address `/clashes` of the API reports the clashes between published runs. See [Runs](../tabs/runs.md).

**A row shows an error when I edit it.** The same checks run on every change. Read the message above the table: it names the sheet, row and column. See [Import and editing errors](import-errors.md).

## Related

- [Run statuses](run-statuses.md)
- [Pre-flight issues](preflight-issues.md)
- [Constraints](../constraints/README.md)
