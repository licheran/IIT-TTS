# Session

Sheet name in Excel and CSV files: `Session`.

## What it is

How each module holds each kind of session. There is **one row for each module and session type**: for example one row for "Software Engineering lectures" and one for "Software Engineering tutorials". The row says which module and which session type, and, only where this module differs from the session type, the setting that differs.

The program makes the actual sessions from these rows: you never type them. See [Activities](Activities.md) for what it produces. A **Session row** is a rule ("this module has tutorials, one group each"). A **session** is one meeting in the timetable that the solver makes from it.

You will not find a `code` column. The row's code is made from its two first columns (`6SENG005C-TUT`), so you only choose the module and the session type.

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `module` | The module this row is about. | text | yes | — | a code from [Modules](Modules.md) |
| `session_type` | The kind of session, for example `LEC` or `TUT`. It becomes the `kind` of the sessions. | text | yes | — | a code from [SessionTypes](SessionTypes.md) |
| `start_pattern` | The start pattern that gives the length and the allowed start times. Blank: the session type's. | text | no | — | a code from [StartPatterns](StartPatterns.md) |
| `delivery` | Whether the session is held in a room or online. Blank: the session type's. | text | no | — | `in_person` or `online` |
| `room_type` | The type of room the session needs. Blank: the session type's. Never used when the session is online. | text | no | — | — |
| `max_groups` | How many groups meet in one session. Blank: the session type's. | whole number ≥ 1 | no | — | — |
| `teachers` | How many teachers take each session. Blank: the session type's. `0` means no teacher is needed. | whole number ≥ 0 | no | — | — |
| `weekly` | How many times a week each group has this session. Blank: the session type's. | whole number ≥ 1 | no | — | — |
| `tags` | Labels of the form `key=value`, separated by `;`. See the Tags page. | key=value pairs | no | — | — |

Tags are explained on the [Tags](tags.md) page.

## Rules

- **A blank cell takes the session type's value.** A filled cell replaces it for this module only. Most rows only need `module` and `session_type`.
- **One row for each pair.** A second row with the same module and session type is an error (`duplicate "6SENG005C" + "LEC"`).
- **A module has the session types its rows list.** A module with no rows has no sessions. If groups take such a module, [pre-flight](../tabs/preflight.md) gives a warning (it does not stop a run).
- **A blank `max_groups` takes the session type's value.** On the Session types table a blank `max_groups` means "all the groups in one session"; here it means "as the session type says". To make one module's lectures hold every group when the session type has a limit, type a number at least as large as the module's groups.
- **An online row has no room.** If the session is online (its own `delivery`, or its session type's), it cannot have a `room_type` (`an online session cannot have a room type`). An in-person row of an online session type must give a `room_type`.
- **Tags.** A session carries the tags of its session type, then those of its module, then those of this row. The later one wins when two give the same key.
- **Teachers.** Which teachers can take the sessions is set on the [Teachers](Teachers.md) table (`modules`), as `6SENG005C` or `6SENG005C:TUT`. A `module:KIND` there needs a row here for that kind.

## Example

| `module` | `session_type` | `start_pattern` | `delivery` | `room_type` | `max_groups` | `teachers` | `weekly` | `tags` |
|---|---|---|---|---|---|---|---|---|
| 6SENG005C | LEC |   |   |   | 4 |   |   |   |
| 6SENG005C | TUT |   |   |   |   |   |   |   |
| 6CCGD007C | LEC |   | online |   | 1 |   |   |   |

The first module's lecture holds up to four groups (the session type says seven), and its tutorial takes everything from the session type (one group each). The last row is an online lecture for one group, so it needs no room.

## Related

- [All tables](README.md)
- [Basics](../basics.md)
- [Session types](SessionTypes.md) and [Modules](Modules.md)
- [Import and editing errors](../troubleshooting/import-errors.md): what each message means and how to fix it
