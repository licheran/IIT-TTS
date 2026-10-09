# Limit per week (`max_load`)

Catalogue entry **C15**. Each selected resource has at most a set number of events or periods in the whole week.

## What it does

For each selected group, teacher or room, the number of **periods occupied** in the week (or of **events**, if `unit` is `events`) must not be more than `max`. It is the weekly version of [`max_per_day`](max_per_day.md).

## Scope

The `scope` of this type selects **resources (groups, teachers, rooms and so on)**. See [Selectors](selectors.md).

## Parameters

| Parameter | Meaning | Type | Required | Default |
|---|---|---|---|---|
| `max` | The most allowed in the week. `0` means the resource may never be used. | whole number ≥ 0 | yes | — |
| `unit` | What to count: `periods` (the default) counts every occupied period, so a 2-period lecture counts 2. `events` counts activities, so it counts 1. | one of `events`, `periods` | no | `periods` |

## How the penalty is counted

For each resource, the amount above `max`, added up. A teacher with 22 periods in the week, with `max` 20, scores 2.

## Hard or soft?

As **hard**, this is a contract limit: no teacher is given more than their hours, and a run that cannot keep to it is `infeasible`. In an academic dataset built from configuration you do not write it by hand: fill the `max_hours` column of the [Teachers](../tables/Teachers.md) table and a hard `LOAD-<teacher>` rule is made for that teacher (see [Default constraints](defaults.md)). As **soft**, it is a preference with a cost for each period over.

## Example row for the Constraints table

| `code` | `type` | `scope` | `params` | `hard` | `weight` | `active` |
|---|---|---|---|---|---|---|
| TEACH-WEEK | max_load | type:Teacher | {"max": 20, "unit": "periods"} | true | 1 | true |

The same row as data:

```json
{
  "code": "TEACH-WEEK",
  "type": "max_load",
  "scope": "type:Teacher",
  "params": {
    "max": 20,
    "unit": "periods"
  },
  "hard": true,
  "weight": 1,
  "active": true
}
```

## Related

- [All constraints](README.md)
- [Selectors](selectors.md)
- [The Constraints table](../tables/Constraints.md)
- [Default constraints](defaults.md)
