# Constraints

Sheet name in Excel and CSV files: `Constraints`.

## What it is

Your timetable rules beyond the ones that always hold. Each row is one rule, hard or soft. A new academic dataset starts with a few default preferences here.

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `code` | A unique name for the rule. It appears in the score breakdown and in error messages. | text | yes | — | — |
| `type` | Which kind of rule: one of the catalogue types (for example `max_gaps`). | text | yes | — | — |
| `scope` | Whom or what the rule covers, as a selector (for example `type:StudentGroup`). | selector | yes | — | — |
| `params` | Settings of the rule, as JSON (for example `{"max": 2, "per": "day"}`). | JSON | no | — | — |
| `hard` | True: the rule **must** hold. False: it is a preference. | true/false | no | true | — |
| `weight` | How much a broken soft rule costs. Ignored when `hard` is true. | whole number ≥ 0 | no | `1` | — |
| `active` | Untick to switch the rule off without deleting it. | true/false | no | true | — |

## Rules

- **`type`** must be one of the catalogue types. Any other name is refused at import. The [constraints section](../constraints/README.md) lists every type and its `params`.
- **`scope`** must pick the right kind of thing for the type: resources for some types, activities for others. The wrong kind is refused at import.
- **Hard** rules are never broken. If they cannot all hold, the run is `infeasible` and the conflicting rules are named. **Soft** rules add `weight × penalty` to the score, and the solver tries to lower it.
- An inactive rule is ignored completely (for example the default `AC-TRAVEL`).
- The automatic lecture-before-tutorial rules are named `AUTO-ORDER:…` and are managed by Expand. Do not edit them.

## Example

An illustration (the L6 sample workbook has no rows in this table):

| `code` | `type` | `scope` | `params` | `hard` | `weight` | `active` |
|---|---|---|---|---|---|---|
| AC-GAPS | max_gaps | type:StudentGroup | {"max": 2, "per": "day"} | false | 5 | true |
| T-DAYS | max_days | type:Teacher | {"max": 4} | true | 1 | true |

## Related

- [All tables](README.md)
- [Basics](../basics.md)
