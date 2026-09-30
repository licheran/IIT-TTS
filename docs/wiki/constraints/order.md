# Order (`order`)

Catalogue entry **C7**. The activities of a sequence follow one another in time.

## What it does

Each activity of `sequence` must **start after the previous one ends**. They may be on different days. With `same_day` they must also be on the same day. The `scope` must select activities, but the activities that are ordered are the ones named in `sequence`.

## Scope

The `scope` of this type selects **activities**. See [Selectors](selectors.md).

## Parameters

| Parameter | Meaning | Type | Required | Default |
|---|---|---|---|---|
| `sequence` | The activity codes, in the order they must happen. At least two. | list of text | yes | — |
| `same_day` | If true, each pair must also be on the same day. Default false. | true/false | no | false |

## How the penalty is counted

The number of neighbouring pairs in the sequence that break the rule. A sequence of three where the third starts before the second ends scores 1.

## Hard or soft?

Expand already adds a soft lecture-before-tutorial rule (weight 1) for each module, with codes that start `AUTO-ORDER:`. Add your own for special cases. An activity named in `sequence` that does not exist is reported by pre-flight as `invalid_constraint`.

## Example row for the Constraints table

| `code` | `type` | `scope` | `params` | `hard` | `weight` | `active` |
|---|---|---|---|---|---|---|
| SENG005-ORDER | order | ref:6SENG005C | {"sequence": ["6SENG005C-LEC-01", "6SENG005C-TUT-01"], "same_day": false} | false | 1 | true |

The same row as data:

```json
{
  "code": "SENG005-ORDER",
  "type": "order",
  "scope": "ref:6SENG005C",
  "params": {
    "sequence": [
      "6SENG005C-LEC-01",
      "6SENG005C-TUT-01"
    ],
    "same_day": false
  },
  "hard": false,
  "weight": 1,
  "active": true
}
```

## Related

- [All constraints](README.md)
- [Selectors](selectors.md)
- [The Constraints table](../tables/Constraints.md)
