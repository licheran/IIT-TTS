# Travel time between buildings (`travel_gap`)

Catalogue entry **C10**. A resource that changes building has free time to travel.

## What it does

For each selected group or teacher, when two of its activities on a day are in **different places** (for example different buildings), there must be at least `min_periods` **free** periods between them. An activity's place is the `level` ancestor of its rooms: with `level` `Building`, the buildings of its rooms. An activity with no room has no place and never counts.

## Scope

The `scope` of this type selects **resources (groups, teachers, rooms and so on)**. See [Selectors](selectors.md).

## Parameters

| Parameter | Meaning | Type | Required | Default |
|---|---|---|---|---|
| `min_periods` | The free periods required between activities in different places. | whole number ≥ 0 | yes | — |
| `level` | The kind of place, as a resource type, normally `Building`. A type that does not exist is reported as `level "…" is not a resource type`. | text | yes | — |

## How the penalty is counted

The number of moves between places that do not get enough free periods. Two back-to-back activities in different buildings with `min_periods` 1 score 1.

## Hard or soft?

The institute needs no free time between buildings, so the default `AC-TRAVEL` is created **switched off**. Switch it on (tick `active`) if that changes. It is a **soft** rule by default.

## Example row for the Constraints table

| `code` | `type` | `scope` | `params` | `hard` | `weight` | `active` |
|---|---|---|---|---|---|---|
| AC-TRAVEL | travel_gap | type:StudentGroup | {"min_periods": 1, "level": "Building"} | false | 10 | false |

The same row as data:

```json
{
  "code": "AC-TRAVEL",
  "type": "travel_gap",
  "scope": "type:StudentGroup",
  "params": {
    "min_periods": 1,
    "level": "Building"
  },
  "hard": false,
  "weight": 10,
  "active": false
}
```

## Related

- [All constraints](README.md)
- [Selectors](selectors.md)
- [The Constraints table](../tables/Constraints.md)
