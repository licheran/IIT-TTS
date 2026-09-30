# Back to back (`consecutive`)

Catalogue entry **C8**. The activities of a sequence follow one another immediately.

## What it does

Each activity of `sequence` must start in **the very next period** after the previous one ends, on the same day. "Next" is literal: a break, or the end of the day, between them breaks the rule.

## Scope

The `scope` of this type selects **activities**. See [Selectors](selectors.md).

## Parameters

| Parameter | Meaning | Type | Required | Default |
|---|---|---|---|---|
| `sequence` | The activity codes, in order. At least two. | list of text | yes | — |

## How the penalty is counted

The number of neighbouring pairs that are not back to back.

## Hard or soft?

To keep two activities as one long block, for example a lecture that must be followed at once by its tutorial. Remember that nothing may cross a break, so the pair must fit on one side of it.

## Example row for the Constraints table

| `code` | `type` | `scope` | `params` | `hard` | `weight` | `active` |
|---|---|---|---|---|---|---|
| BACK-TO-BACK | consecutive | ref:6COSC021C | {"sequence": ["6COSC021C-LEC-01", "6COSC021C-TUT-01"]} | false | 2 | true |

The same row as data:

```json
{
  "code": "BACK-TO-BACK",
  "type": "consecutive",
  "scope": "ref:6COSC021C",
  "params": {
    "sequence": [
      "6COSC021C-LEC-01",
      "6COSC021C-TUT-01"
    ]
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
