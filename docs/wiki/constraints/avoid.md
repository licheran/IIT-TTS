# Avoid marked times (`avoid`)

Catalogue entry **C13**. Selected resources are not used in the slots marked `avoid` in Availability.

## What it does

This type makes the `avoid` rows of the [Availability](../tables/Availability.md) table count. A resource in the scope should not be occupied in the slots that its own Availability rows mark `avoid`.

## Scope

The `scope` of this type selects **resources (groups, teachers, rooms and so on)**. See [Selectors](selectors.md).

## Parameters

This type has no parameters. Leave `params` blank, or write `{}`.

## How the penalty is counted

The number of occupied `avoid` periods, added up over the resources.

## Hard or soft?

**Without a constraint of this type, `avoid` rows in Availability have no effect.** Add one row, for example scope `type:Teacher`, soft, to honour teachers' preferences. `unavailable` rows do not need it: they always hold.

## Example row for the Constraints table

| `code` | `type` | `scope` | `params` | `hard` | `weight` | `active` |
|---|---|---|---|---|---|---|
| TEACHER-AVOID | avoid | type:Teacher |  | false | 3 | true |

The same row as data:

```json
{
  "code": "TEACHER-AVOID",
  "type": "avoid",
  "scope": "type:Teacher",
  "params": {},
  "hard": false,
  "weight": 3,
  "active": true
}
```

## Related

- [All constraints](README.md)
- [Selectors](selectors.md)
- [The Constraints table](../tables/Constraints.md)
