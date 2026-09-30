# Same day (`same_day`)

Catalogue entry **C6**. All selected activities are on the same day.

## What it does

All activities in the scope must be on the **same day**. They may start in different periods.

## Scope

The `scope` of this type selects **activities**. See [Selectors](selectors.md).

## Parameters

This type has no parameters. Leave `params` blank, or write `{}`.

## How the penalty is counted

The number of activities that are not on the most common day.

## Hard or soft?

Keep a module's sessions together on one day, for example all the tutorials of one module. Use `same_start` if they must also start together.

## Example row for the Constraints table

| `code` | `type` | `scope` | `params` | `hard` | `weight` | `active` |
|---|---|---|---|---|---|---|
| TUTS-ONE-DAY | same_day | kind:TUT;ref:6COSC021C |  | false | 2 | true |

The same row as data:

```json
{
  "code": "TUTS-ONE-DAY",
  "type": "same_day",
  "scope": "kind:TUT;ref:6COSC021C",
  "params": {},
  "hard": false,
  "weight": 2,
  "active": true
}
```

## Related

- [All constraints](README.md)
- [Selectors](selectors.md)
- [The Constraints table](../tables/Constraints.md)
