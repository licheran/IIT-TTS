# Preferred rooms (`preferred_resources`)

Catalogue entry **C12**. The rooms chosen for the selected activities match a selector.

## What it does

Every room the solver chooses for an activity in the scope should match the `filter`, a selector over resources.

## Scope

The `scope` of this type selects **activities**. See [Selectors](selectors.md).

## Parameters

| Parameter | Meaning | Type | Required | Default |
|---|---|---|---|---|
| `filter` | A selector that picks resources, for example `under:GP` for the rooms of building GP, or `type:Room;attr:capacity>=60`. | text | yes | — |

## How the penalty is counted

The number of chosen rooms that do not match.

## Hard or soft?

The hard requirement of an activity is its `room_type` and the capacity. Use this for a **preference** on top, such as a particular building. As **hard**, it narrows the candidate rooms, which can leave none.

## Example row for the Constraints table

| `code` | `type` | `scope` | `params` | `hard` | `weight` | `active` |
|---|---|---|---|---|---|---|
| PREFER-GP | preferred_resources | kind:TUT | {"filter": "under:GP"} | false | 2 | true |

The same row as data:

```json
{
  "code": "PREFER-GP",
  "type": "preferred_resources",
  "scope": "kind:TUT",
  "params": {
    "filter": "under:GP"
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
