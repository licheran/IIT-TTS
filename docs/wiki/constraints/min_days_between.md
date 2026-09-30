# Days between activities (`min_days_between`)

Catalogue entry **C4**. Any two selected activities are at least a set number of days apart.

## What it does

Every **pair** of activities in the scope must be at least `min` days apart. `min` 1 means two different days. `min` 2 means at least one free day between them.

## Scope

The `scope` of this type selects **activities**. See [Selectors](selectors.md).

## Parameters

| Parameter | Meaning | Type | Required | Default |
|---|---|---|---|---|
| `min` | The smallest number of days between two activities. | whole number ≥ 0 | yes | — |

## How the penalty is counted

The number of pairs that are closer than `min` days. Three activities, two of which fall on the same day, with `min` 1, score 1.

## Hard or soft?

Spread the lectures of a module over the week (select them with `kind:LEC;ref:<module>`), or spread a cohort's exams. The exams preset's default `EX-SPREAD-…` constraints are this type. Activities without a place are ignored.

## Example row for the Constraints table

| `code` | `type` | `scope` | `params` | `hard` | `weight` | `active` |
|---|---|---|---|---|---|---|
| SPREAD-SENG005 | min_days_between | kind:LEC;ref:6SENG005C | {"min": 1} | false | 3 | true |

The same row as data:

```json
{
  "code": "SPREAD-SENG005",
  "type": "min_days_between",
  "scope": "kind:LEC;ref:6SENG005C",
  "params": {
    "min": 1
  },
  "hard": false,
  "weight": 3,
  "active": true
}
```

## Related

- [All constraints](README.md)
- [Selectors](selectors.md)
- [The Constraints table](../tables/Constraints.md)
