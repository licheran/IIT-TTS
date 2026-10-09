# Even load (`balance_load`)

Catalogue entry **C16**. The selected resources carry the same load over the week.

## What it does

For the selected resources taken together, the weekly load (the **periods occupied**, or the **events** if `unit` is `events`) should be the same. The rule looks at the most loaded and the least loaded of them. With fewer than two resources there is nothing to balance.

## Scope

The `scope` of this type selects **resources (groups, teachers, rooms and so on)**. See [Selectors](selectors.md).

## Parameters

| Parameter | Meaning | Type | Required | Default |
|---|---|---|---|---|
| `unit` | What to count: `periods` (the default) counts every occupied period; `events` counts activities. | one of `events`, `periods` | no | `periods` |

## How the penalty is counted

The load of the most loaded resource minus the load of the least loaded one. Three teachers with 10, 8 and 6 periods score 10 − 6 = 4.

## Hard or soft?

Usually **soft**: perfect equality is rarely possible, and the score tells you how far from it you are. Cover the people who should share the work, for example `code:HAWE,HARR`. In an academic dataset built from configuration a soft `FAIR-<module>` rule is made for every module with two or more teachers (see [Default constraints](defaults.md)). As **hard**, it asks for exactly equal loads and is seldom possible.

## Example row for the Constraints table

| `code` | `type` | `scope` | `params` | `hard` | `weight` | `active` |
|---|---|---|---|---|---|---|
| SHARE-LOAD | balance_load | type:Teacher | {"unit": "periods"} | false | 2 | true |

The same row as data:

```json
{
  "code": "SHARE-LOAD",
  "type": "balance_load",
  "scope": "type:Teacher",
  "params": {
    "unit": "periods"
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
- [Default constraints](defaults.md)
