# Tags

## What they are

A **tag** is a small label in the form `key=value` that you attach to a row, for example `floor=2` on a room or `university=UOW` on a group. Tags do nothing by themselves. They become useful when a rule or template picks rows **by tag**, for example "every lab on floor 2".

Tags are the way to make your own groupings without adding tables.

## How to write them

A `tags` cell holds pairs separated by `;`:

```
university=UOW;floor=2
```

The rules:

- Each pair is `key=value`. The first `=` splits the pair, so a value may itself contain `=`.
- Keys and values are trimmed of spaces at both ends. A value may be empty (`wing=`). A key may not be empty.
- A key may appear **once per row**. `floor=2;floor=3` is refused with `duplicate key "floor"`.
- Neither a key nor a value can contain `;` (it separates the pairs), and a key cannot contain `=`.
- Keys and values are **case-sensitive**: `floor=2` and `Floor=2` are different tags.
- Lists of pairs that are not of the form `key=value` are refused with `expected key=value pairs separated by ";", got "…"`.

In the table editor, a tags cell opens an editor with one row for each `key` and `value`, an **Add tag** button and a remove button. In the entry row under the headers you type the text form `floor=2;wing=B`.

## Which tables have tags

| Table | Tags column | Notes |
|---|---|---|
| [Universities](Universities.md) | yes | |
| [Levels](Levels.md) | yes | |
| [Programmes](Programmes.md) | yes | |
| [Groups](Groups.md) | yes | |
| [Teachers](Teachers.md) | yes | |
| [Campuses](Campuses.md) | yes | |
| [Buildings](Buildings.md) | yes | |
| [Rooms](Rooms.md) | yes | Also has the `room_type` column, which is stored as the tag `room_type` |
| [SessionTypes](SessionTypes.md) | yes | Tags on a session type are given to every session made from it |
| [Modules](Modules.md) | yes | |
| [Activities](Activities.md) | yes | Tags on an activity are matched by rules that select activities |
| Every other table | no | Templates, join tables, Availability, Constraints, Pins and the rest have no tags |

## The one tag the program reads for itself

**`room_type`** on a room. The column `room_type` of the Rooms table is saved as the tag `room_type=<value>`. An activity (or template) that asks for a room type, for example `lab`, can only be given rooms whose `room_type` tag is exactly that value. Because it has its own column, do not also put `room_type=…` in a room's `tags`.

Every other tag is yours. The program stores it and gives it back, and otherwise ignores it unless you use it in a selector.

## How to use tags: selectors

A **selector** is the short text that picks rows. It is used in the `scope` of a constraint, in the `groups` of a template, and in the `filter` of a few constraint types. The tag clauses are:

| Clause | Picks |
|---|---|
| `tag:floor=2` | rows whose tag `floor` equals `2` |
| `tag:floor!=2` | rows whose tag `floor` is **not** `2`, **including rows that have no `floor` tag at all** |

Clauses combine with `;` (all of them must match). A few examples:

| Selector | Picks |
|---|---|
| `type:Room;tag:room_type=lab` | every lab |
| `type:Room;tag:floor=2` | every room on floor 2 |
| `type:StudentGroup;tag:university=UOW` | every group tagged for the UOW |
| `type:Room;tag:room_type=lab;tag:wing!=B` | labs that are not in wing B, or have no wing |

A tag belongs to **the row itself**. A group does not inherit its programme's tags: tag the groups if you want to select groups. To select everything below a programme, use `under:` instead (see [Selectors](../constraints/selectors.md)).

## Suggested tags

These are only ideas. The program does not know them, and you can invent any.

| On | Tag | Use |
|---|---|---|
| Levels, programmes, groups | `university=UOW` | Select or constrain by awarding university |
| Rooms | `floor=2`, `wing=B`, `accessible=yes` | Prefer or avoid parts of a building |
| Teachers | `contract=part_time` | Give part-timers a stricter limit on days, with a scope like `tag:contract=part_time` |
| Activities | `block=morning` | Pick a set of activities for a rule such as a preferred time |

The FET import marks each activity with `fet_label=<its original time label>`. It is kept for reference only.

## Related

- [Selectors](../constraints/selectors.md)
- [All tables](README.md)
- [Basics](../basics.md)
