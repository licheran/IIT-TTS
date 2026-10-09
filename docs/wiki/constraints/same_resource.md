# Same teacher, same room (`same_resource`)

Catalogue entry **C17**. The activities of a resource use the same resource of another type.

## What it does

For each resource of the type named in `per` (for example each **group**), the selected activities it attends should all use the same resource of the type named in `type` (for example the same **teacher**). The resource can be fixed on the activity or chosen by the solver.

## Scope

The `scope` of this type selects **activities**. See [Selectors](selectors.md).

## Parameters

| Parameter | Meaning | Type | Required | Default |
|---|---|---|---|---|
| `type` | The type of resource that should stay the same, for example `Teacher`. | text | yes | — |
| `per` | The type of resource the rule is checked for, for example `StudentGroup`. | text | yes | — |

## How the penalty is counted

For each resource of type `per`: its selected activities, minus the number that use its most common resource of type `type`. A group with three tutorials taught by HAWE, HAWE and HARR scores 3 − 2 = 1. The scores of all the groups are added.

## Hard or soft?

Usually **soft**: sometimes a group cannot keep one teacher. Choose the activities in the scope: `ref:6SENG005C;kind:TUT` means "all tutorials of one module". In an academic dataset built from configuration a soft `CONT-<module>-<kind>` rule is made for every module and kind with two or more teachers (see [Default constraints](defaults.md)). If a type name does not exist in the dataset the rule has nothing to compare and scores 0.

## Example row for the Constraints table

| `code` | `type` | `scope` | `params` | `hard` | `weight` | `active` |
|---|---|---|---|---|---|---|
| SAME-TEACHER | same_resource | kind:TUT | {"type": "Teacher", "per": "StudentGroup"} | false | 3 | true |

The same row as data:

```json
{
  "code": "SAME-TEACHER",
  "type": "same_resource",
  "scope": "kind:TUT",
  "params": {
    "type": "Teacher",
    "per": "StudentGroup"
  },
  "hard": false,
  "weight": 3,
  "active": true
}
```

## Related

- [All constraints](README.md)
- [Selectors](selectors.md)
- [The Constraints table](../tables/Constraints.md)
- [Default constraints](defaults.md)
