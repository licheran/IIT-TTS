# Days in the week (`max_days`)

Catalogue entry **C3**. Each selected resource is busy on at most a set number of days of the week.

## What it does

A **busy day** is a day on which the resource has at least one activity. The number of busy days in the week must not be more than `max`.

## Scope

The `scope` of this type selects **resources (groups, teachers, rooms and so on)**. See [Selectors](selectors.md).

## Parameters

| Parameter | Meaning | Type | Required | Default |
|---|---|---|---|---|
| `max` | The most busy days allowed. | whole number ≥ 0 | yes | — |

## How the penalty is counted

For each resource, the busy days above `max`. A teacher busy Monday, Tuesday, Thursday and Friday with `max` 3 scores 1.

## Hard or soft?

Useful to let part-time teachers come in on few days (give them a tag, such as `contract=part_time`, and use it in the scope). As **hard**, make sure the teacher's activities fit in that many days.

## Example row for the Constraints table

| `code` | `type` | `scope` | `params` | `hard` | `weight` | `active` |
|---|---|---|---|---|---|---|
| PT-DAYS | max_days | type:Teacher;tag:contract=part_time | {"max": 3} | false | 4 | true |

The same row as data:

```json
{
  "code": "PT-DAYS",
  "type": "max_days",
  "scope": "type:Teacher;tag:contract=part_time",
  "params": {
    "max": 3
  },
  "hard": false,
  "weight": 4,
  "active": true
}
```

## Related

- [All constraints](README.md)
- [Selectors](selectors.md)
- [The Constraints table](../tables/Constraints.md)
