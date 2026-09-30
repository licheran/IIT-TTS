# Preferred start times (`preferred_times`)

Catalogue entry **C11**. Each selected activity starts in one of a list of slots.

## What it does

Each activity in the scope must **start** in one of the listed slots. A slot is written `Day:Period`, using the codes of your Days and Periods tables, for example `Mon:P01`. Only the start counts, not the periods the activity goes on to cover.

## Scope

The `scope` of this type selects **activities**. See [Selectors](selectors.md).

## Parameters

| Parameter | Meaning | Type | Required | Default |
|---|---|---|---|---|
| `slots` | The allowed start slots, each written `Day:Period`. At least one. A slot that is not written that way, or names an unknown day or period, is reported by pre-flight. | list of text | yes | — |

## How the penalty is counted

1 for each activity that starts somewhere else.

## Hard or soft?

To keep activities out of unpopular times, list every slot you do accept (there is no "not these" form). The academic default `AC-SAT` lists all the non-Saturday slots, which asks for lectures and tutorials not to be put on Saturdays.

## Example row for the Constraints table

| `code` | `type` | `scope` | `params` | `hard` | `weight` | `active` |
|---|---|---|---|---|---|---|
| MORNING-LECTURES | preferred_times | kind:LEC | {"slots": ["Mon:P01", "Mon:P03", "Tue:P01", "Tue:P03"]} | false | 2 | true |

The same row as data:

```json
{
  "code": "MORNING-LECTURES",
  "type": "preferred_times",
  "scope": "kind:LEC",
  "params": {
    "slots": [
      "Mon:P01",
      "Mon:P03",
      "Tue:P01",
      "Tue:P03"
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
