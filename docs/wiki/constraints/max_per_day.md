# Limit per day (`max_per_day`)

Catalogue entry **C1**. Each selected resource has at most a set number of events or periods a day.

## What it does

For each selected group, teacher or room and for each day, the number of **periods occupied** (or of **events**, if `unit` is `events`) must not be more than `max`.

## Scope

The `scope` of this type selects **resources (groups, teachers, rooms and so on)**. See [Selectors](selectors.md).

## Parameters

| Parameter | Meaning | Type | Required | Default |
|---|---|---|---|---|
| `max` | The most allowed in one day. `0` means the resource may never be used. | whole number ≥ 0 | yes | — |
| `unit` | What to count: `periods` (the default) counts every occupied period, so a 2-period lecture counts 2. `events` counts activities, so it counts 1. | one of `events`, `periods` | no | `periods` |

## How the penalty is counted

For each resource and day, the amount above `max`, added up. A teacher with 8 periods on Tuesday and 7 on Thursday, with `max` 6, scores 2 + 1 = 3.

## Hard or soft?

Good as **hard** for a real workload limit, such as a teacher's maximum teaching hours. As **soft**, use it for a preference such as "students should not have more than 6 periods in a day". A hard limit lower than the work a resource has to do in the days it is available makes the run infeasible.

## Example row for the Constraints table

| `code` | `type` | `scope` | `params` | `hard` | `weight` | `active` |
|---|---|---|---|---|---|---|
| TEACH-DAY | max_per_day | type:Teacher | {"max": 6, "unit": "periods"} | true | 1 | true |

The same row as data:

```json
{
  "code": "TEACH-DAY",
  "type": "max_per_day",
  "scope": "type:Teacher",
  "params": {
    "max": 6,
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
