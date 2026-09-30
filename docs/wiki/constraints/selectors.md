# Selectors

## What they are

A **selector** is a short piece of text that picks out rows: "every teacher", "the groups of the SE programme", "all tutorials of one module". You write selectors in three places:

- the `scope` of a row in [Constraints](../tables/Constraints.md),
- the `groups` of a row in [Templates](../tables/Templates.md),
- the `filter` parameter of a [`preferred_resources`](preferred_resources.md) constraint, and inside `uses:(…)`.

A selector picks either **resources** (groups, teachers, rooms, buildings and so on) or **activities**. Which one depends on where you use it: the type of a constraint says which, and a template's `groups` picks resources.

## How to write one

A selector is either the word `all`, or one or more **clauses** separated by `;`. A row must match **all** the clauses (they are joined with AND). For example:

```
type:Room;tag:room_type=lab;attr:capacity>=60
```

means "rooms, that are labs, that seat 60 or more".

Each clause is `name:value`.

## The clauses

| Clause | Picks | Meaning |
|---|---|---|
| `type:<Type>` | resources | Resources of that type, for example `type:Teacher`, `type:StudentGroup`, `type:Room` |
| `code:<c1>,<c2>` | both | The listed codes. A comma separates several |
| `under:<code>` | resources | The **exclusive** resources below that resource in the hierarchy: the groups of a programme, the rooms of a building |
| `tag:<key>=<value>` | both | Rows whose tag has that value. See [Tags](../tables/tags.md) |
| `tag:<key>!=<value>` | both | Rows whose tag is **not** that value, including rows without the tag |
| `attr:<name><op><value>` | resources | A comparison on an attribute. `capacity` (a group's size or a room's seats) counts as an attribute. Operators: `=`, `!=`, `<`, `<=`, `>`, `>=` |
| `kind:<k1>,<k2>` | activities | Activities of the listed kinds, for example `kind:LEC,TUT` |
| `ref:<code>` | activities | Activities that belong to that module (their reference) |
| `uses:(<selector>)` | activities | Activities that involve a resource matching the inner selector, for example `uses:(under:L6 SE)` |
| `all` | both | Everything |

"Picks resources" means the clause can only be used where resources are wanted. Using it where activities are wanted is refused, for example `clause "kind:" does not select resources`.

### Notes

- **`under:` picks exclusive resources only.** `under:L6` gives the groups below the level `L6`, not the programmes in between. Groups, teachers and rooms are exclusive. Levels and programmes are not.
- **`type:` uses the type's code**, such as `StudentGroup`, not the word shown in the app (`Group`).
- **A missing tag is "not equal".** `tag:wing!=B` picks rooms that have no `wing` tag at all as well as rooms in any other wing.
- **`uses:` looks at who is involved.** `uses:(code:HAWE)` picks every activity that teacher HAWE teaches. An activity for a programme uses each group below it.
- Values are **case-sensitive** and have spaces trimmed at both ends.

### Quoting

Codes can contain spaces and `/`, for example `L6 SE / G1`, and need no quotes: `under:L6 SE`.

A value that contains `;` or `,` must be put in double quotes: `code:"Lab, east"`. Inside the quotes, write `\"` for a quote and `\\` for a backslash. A value with parentheses inside `uses:(…)` should be quoted as well.

## Examples from the L6 sample

| Selector | Picks | In L6 |
|---|---|---|
| `type:StudentGroup` | every group | 30 groups |
| `under:L6 SE` | the groups of the SE programme | 11 groups |
| `under:L6` | every group of the level | 30 groups |
| `type:Room;tag:room_type=lab` | every lab | 9 rooms |
| `type:Room;tag:room_type=lab;attr:capacity>=60` | labs that seat 60 or more | 5 rooms |
| `type:Room;attr:capacity>=100` | large rooms | 4 rooms |
| `type:Room;tag:room_type!=lab` | rooms that are not labs | 1 room |
| `code:AAM,ABM` | two teachers | 2 teachers |
| `code:"L6 SE / G1","L6 SE / G2"` | two groups (the quotes are optional here) | 2 groups |
| `kind:TUT` | every tutorial | 55 activities |
| `kind:LEC;ref:6SENG005C` | the lectures of one module | 3 activities |
| `uses:(under:L6 SE)` | activities that any SE group attends | 26 activities |
| `kind:TUT;uses:(code:AAM)` | tutorials taught by AAM | 1 activity |
| `all` | everything | every resource, or every activity |

## When a selector is wrong

The app reports the problem with the position in the text. Typical messages:

| Message | Cause | Fix |
|---|---|---|
| `unknown clause "teacher:"` | The word before `:` is not a clause name | Use one of the names in the table above. To pick teachers, write `type:Teacher` |
| `type: needs a value` | A clause with nothing after the `:` | Add the value |
| `expected "name:value" but found "under"` | A clause without a `:` | Write `under:<code>` |
| `expected a clause` | A `;` with nothing after it | Remove the trailing `;` |
| `uses: expects a selector in parentheses, "uses:(...)"` | `uses:` without brackets | Write `uses:(…)` |
| `a value containing "," must be quoted` | A comma in a single-value clause | Put the value in double quotes |
| `unterminated quoted value` | A `"` with no closing `"` | Close the quote |
| `empty selector` | Nothing was written | Write `all`, or a clause |
| `clause "kind:" does not select resources` | The clause picks activities but the place wants resources, or the other way round | Use a clause of the right kind |

A selector that is valid but matches nothing is not an error. For a soft constraint, pre-flight shows the warning `empty_scope`.

## Related

- [Constraints](README.md)
- [Tags](../tables/tags.md)
- [Templates](../tables/Templates.md)
