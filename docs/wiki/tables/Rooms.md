# Rooms

Sheet name in Excel and CSV files: `Rooms`.

## What it is

The rooms activities can use. **A room is an exclusive resource: one activity at a time.** The solver chooses the room; you only say what each room is like.

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `code` | The unique name of this row. Other tables refer to it. | text | yes | — | — |
| `name` | A longer name for people. Free text. It is not used for matching. | text | no | — | — |
| `building` | The building the room is in. Optional. | text | no | — | a code from [Buildings](Buildings.md) |
| `capacity` | How many people the room seats. The solver picks rooms whose capacity is at least the sum of the group sizes. | whole number ≥ 0 | no | — | — |
| `room_type` | What kind of room it is, for example `lab`, `auditorium`, `classroom`. Activities ask for a room type. | text | yes | — | stored as the tag `room_type` |
| `tags` | Labels of the form `key=value`, separated by `;`. See the Tags page. | key=value pairs | no | — | — |

Tags are explained on the [Tags](tags.md) page.

## Rules

- **`room_type` is required.** It is saved as the tag `room_type=<value>` (see the Tags page), and an activity that asks for `lab` can only use rooms with `room_type` `lab`.
- Room sizes are realistically 30 to 120, but any number is allowed. The **largest room is a hard limit**: an activity for more students than any room of its type seats cannot be scheduled, and pre-flight says so (`no_candidate`).
- Room types are free text. The spelling must match exactly between the room and the activity that asks for it.

## Example

From the L6 sample:

| `code` | `name` | `building` | `capacity` | `room_type` | `tags` |
|---|---|---|---|---|---|
| Auditorium | Auditorium | GP | 250 | auditorium |   |
| [1LA] -GP | [1LA] -GP | GP | 30 | lab |   |

## Related

- [All tables](README.md)
- [Basics](../basics.md)
