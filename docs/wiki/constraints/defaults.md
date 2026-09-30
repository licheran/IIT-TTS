# Default constraints

## What they are

Some preferences are so common that the presets supply them ready-made. They are ordinary rows of the [Constraints](../tables/Constraints.md) table: you can edit, switch off (untick `active`) or delete any of them.

## Academic preset

A **new academic dataset** created in the app starts with these three rows.

| Code | Type | Covers | Parameters | Hard | Weight | Active | In plain words |
|---|---|---|---|---|---|---|---|
| `AC-GAPS` | [`max_gaps`](max_gaps.md) | `type:StudentGroup` | `{"max": 2, "per": "day"}` | no | 5 | yes | A group should have at most 2 free periods inside a day |
| `AC-TGAPS` | [`max_gaps`](max_gaps.md) | `type:Teacher` | `{"max": 3, "per": "day"}` | no | 2 | yes | A teacher should have at most 3 free periods inside a day |
| `AC-TRAVEL` | [`travel_gap`](travel_gap.md) | `type:StudentGroup` | `{"min_periods": 1, "level": "Building"}` | no | 10 | **no** | A group that changes building needs one free period. **Switched off**, because the institute needs no free time for a change of building |

To use `AC-TRAVEL`, tick its `active` box in the Constraints table.

And one more that exists only in a special case:

| Code | Type | Covers | Parameters | Hard | Weight | In plain words |
|---|---|---|---|---|---|---|
| `AC-SAT` | [`preferred_times`](preferred_times.md) | `kind:LEC,TUT` | every slot of every day except Saturday | no | 3 | Lectures and tutorials should not be placed on Saturday |

`AC-SAT` is made only by the command `tts import-fet`, and only when the imported timetable has a Saturday. A dataset created in the app starts with no days, so it never gets `AC-SAT`. To get the same effect, add a `preferred_times` row yourself, listing the slots you accept.

### Good to know

- **Importing a workbook replaces the constraints** with the workbook's Constraints sheet. If it is empty, the three defaults are gone. Put your rows in the workbook, or add the defaults back by hand from the table above.
- The command `tts import-fet` adds the defaults to the workbook it writes, unless you pass `--no-defaults`. The L6 sample `l6.xlsx` was written with `--no-defaults`, so it has no constraints. With the defaults, L6 scores 0: every preference is met.
- The Run tab's score breakdown lists these rules by their codes.

## Lecture before tutorial

When you run **Expand** on Templates, the program also adds one soft [`order`](order.md) rule for each lecture-and-tutorial pair of a module that share a group, with weight 1. Their codes start with `AUTO-ORDER:`. They are managed by Expand: it adds, changes and removes them as the templates change, so do not edit them by hand.

## Exams preset

| Code | Type | Covers | Parameters | Hard | Weight | In plain words |
|---|---|---|---|---|---|---|
| `EX-SPREAD-<cohort>` | [`min_days_between`](min_days_between.md) | the exams that cohort sits: `uses:(code:"<cohort>")` | `{"min": 2}` | no | 1 | A cohort's exams should have at least one free day between them |

There is one row for each cohort. They are part of the exams sample workbook. A new exams dataset created in the app starts with none, because it has no cohorts yet: add one row for each cohort, or import a workbook that has them.

## Related

- [Constraints](README.md)
- [The Constraints table](../tables/Constraints.md)
