# Same start (`same_start`)

Catalogue entry **C5**. All selected activities start at the same day and period.

## What it does

All activities in the scope must start in the **same slot**: the same day and the same period.

## Scope

The `scope` of this type selects **activities**. See [Selectors](selectors.md).

## Parameters

This type has no parameters. Leave `params` blank, or write `{}`.

## How the penalty is counted

The number of activities that are not at the most common start. Four activities, three starting Monday `P01` and one starting Monday `P03`, score 1.

## Hard or soft?

For sessions that have to run in parallel, for example the tutorials of one module for different groups. A **hard** `same_start` needs the resources of each activity to be free at the same time.

## Example row for the Constraints table

| `code` | `type` | `scope` | `params` | `hard` | `weight` | `active` |
|---|---|---|---|---|---|---|
| TUT-PARALLEL | same_start | kind:TUT;ref:6SENG005C |  | false | 2 | true |

The same row as data:

```json
{
  "code": "TUT-PARALLEL",
  "type": "same_start",
  "scope": "kind:TUT;ref:6SENG005C",
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
