# Length of the day (`max_span`)

Catalogue entry **C14**. The day of a resource, from first to last activity, is at most a set number of periods long.

## What it does

On each day, from the **first** occupied period to the **last** inclusive, the span must not be longer than `max` periods. Periods are counted by position, so a lunch break inside the span counts towards it.

## Scope

The `scope` of this type selects **resources (groups, teachers, rooms and so on)**. See [Selectors](selectors.md).

## Parameters

| Parameter | Meaning | Type | Required | Default |
|---|---|---|---|---|
| `max` | The longest span, in periods. | whole number ≥ 0 | yes | — |

## How the penalty is counted

The excess over `max`, added up over days and resources. A group with activities in `P01` and `P08` has a span of 8. With `max` 6 that scores 2.

## Hard or soft?

Stops days from being stretched from early morning to late evening even when the gaps themselves are few. Usually **soft**.

## Example row for the Constraints table

| `code` | `type` | `scope` | `params` | `hard` | `weight` | `active` |
|---|---|---|---|---|---|---|
| SHORT-DAYS | max_span | type:StudentGroup | {"max": 8} | false | 2 | true |

The same row as data:

```json
{
  "code": "SHORT-DAYS",
  "type": "max_span",
  "scope": "type:StudentGroup",
  "params": {
    "max": 8
  },
  "hard": false,
  "weight": 2,
  "active": true
}
```

## Related

- [All constraints](README.md)
- [Selectors](selectors.md)
- [The Constraints table](../tables/Constraints.md)
