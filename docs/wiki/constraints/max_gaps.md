# Gaps (`max_gaps`)

Catalogue entry **C2**. Each selected resource has at most a set number of free periods inside its day.

## What it does

A **gap** is a free period on a day that lies between the resource's first and last occupied period and is not a break. A group that has activities in `P01`, `P02` and `P04` has one gap, `P03`. Break periods never count as gaps. The number of gaps must not exceed `max`, per day or over the whole week.

## Scope

The `scope` of this type selects **resources (groups, teachers, rooms and so on)**. See [Selectors](selectors.md).

## Parameters

| Parameter | Meaning | Type | Required | Default |
|---|---|---|---|---|
| `max` | The gaps allowed. | whole number ≥ 0 | yes | — |
| `per` | `day` (the default): the limit applies to each day separately. `week`: one limit for the sum of the week's gaps. | one of `day`, `week` | no | `day` |

## How the penalty is counted

With `per` = `day`: for each resource and day, the gaps above `max`, added up. With `per` = `week`: the week's gaps above `max`. A group with gaps 2, 0, 1, 3 on four days and `max` 1 scores 1 + 0 + 0 + 2 = 3 per day, or 6 − 1 = 5 per week.

## Hard or soft?

The classic **soft** rule: fewer idle hours between classes. The academic defaults `AC-GAPS` (groups) and `AC-TGAPS` (teachers) are this type. Making it hard with a small `max` is rarely possible with busy groups.

## Example row for the Constraints table

| `code` | `type` | `scope` | `params` | `hard` | `weight` | `active` |
|---|---|---|---|---|---|---|
| AC-GAPS | max_gaps | type:StudentGroup | {"max": 2, "per": "day"} | false | 5 | true |

The same row as data:

```json
{
  "code": "AC-GAPS",
  "type": "max_gaps",
  "scope": "type:StudentGroup",
  "params": {
    "max": 2,
    "per": "day"
  },
  "hard": false,
  "weight": 5,
  "active": true
}
```

## Related

- [All constraints](README.md)
- [Selectors](selectors.md)
- [The Constraints table](../tables/Constraints.md)
