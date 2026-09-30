# Do not overlap (`not_overlapping`)

Catalogue entry **C9**. No two selected activities share a period, even if they share no resource.

## What it does

No two activities in the scope may be in the same period, even when they involve different groups, teachers and rooms.

## Scope

The `scope` of this type selects **activities**. See [Selectors](selectors.md).

## Parameters

This type has no parameters. Leave `params` blank, or write `{}`.

## How the penalty is counted

The number of pairs of activities that overlap in time.

## Hard or soft?

Use it when the same students may take two modules that are not linked in the data, such as two options, or when an outside person attends both. As **hard**, it can force a lot of the week apart.

## Example row for the Constraints table

| `code` | `type` | `scope` | `params` | `hard` | `weight` | `active` |
|---|---|---|---|---|---|---|
| OPTIONS-APART | not_overlapping | code:6COSC021C-LEC-01,6SENG005C-LEC-01 |  | true | 1 | true |

The same row as data:

```json
{
  "code": "OPTIONS-APART",
  "type": "not_overlapping",
  "scope": "code:6COSC021C-LEC-01,6SENG005C-LEC-01",
  "params": {},
  "hard": true,
  "weight": 1,
  "active": true
}
```

## Related

- [All constraints](README.md)
- [Selectors](selectors.md)
- [The Constraints table](../tables/Constraints.md)
