# Session types

Sheet name in Excel and CSV files: `SessionTypes`.

## What it is

The kinds of session a module can have, such as a lecture, a tutorial or a lab, and the settings each one has: how long it is, whether it is online, what kind of room it needs, how many groups meet together, and how often it happens in a week. You define each kind **once** here, and every module that lists it gets the same settings (a module can change them for itself, see [Modules](Modules.md)).

The program makes the actual sessions from these settings: you never type them. See [Activities](Activities.md) for what it produces.

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `code` | The kind's code, for example `LEC` or `TUT`. Modules refer to it, and it is the `kind` shown on each session. | text | yes | — | — |
| `name` | A longer name for people, for example `Lecture`. | text | no | — | — |
| `start_pattern` | The start pattern that gives the length of the session and the times it may start. | text | yes | — | a code from [StartPatterns](StartPatterns.md) |
| `delivery` | Whether the session is held in a room or online. An online session has no room. | text | no | `in_person` | `in_person` or `online` |
| `room_type` | The type of room the session needs, matching the `room_type` of a room. Leave blank for an online session. | text | yes, when delivery is in_person | — | — |
| `max_groups` | How many groups meet in one session. Leave blank to put all the module's groups in one session. | whole number ≥ 1 | no | — | — |
| `teachers` | How many teachers take each session. `0` means no teacher is needed. | whole number ≥ 0 | no | `1` | — |
| `weekly` | How many times a week each group has this session. Its sessions always have the same groups. | whole number ≥ 1 | no | `1` | — |
| `tags` | Labels of the form `key=value`, separated by `;`. See the Tags page. | key=value pairs | no | — | — |

Tags are explained on the [Tags](tags.md) page.

## Rules

- **The room must seat everyone.** Its capacity must be at least the sum of the sizes of the groups in the session, and its `room_type` must match exactly.
- **`max_groups` sets the number of sessions.** The program works out how many sessions a module needs from its groups: 10 groups with `max_groups` 3 need `⌈10 ÷ 3⌉` = 4 sessions. The solver decides which groups go together, and keeps the sizes as even as it can (3 + 3 + 2 + 2, never 3 + 3 + 3 + 1).
- **A group keeps the same companions.** When `weekly` is 2, a group meets the same other groups in both of its sessions.
- An online session cannot have a room type (`an online session cannot have a room type`). An in-person session must have one.
- A session type does nothing until a module lists it in its `sessions` column.

## Example

| `code` | `name` | `start_pattern` | `delivery` | `room_type` | `max_groups` | `teachers` | `weekly` | `tags` |
|---|---|---|---|---|---|---|---|---|
| LEC | Lecture | 2H | in_person | lab | 7 | 1 | 1 |   |
| TUT | Tutorial | 2H | in_person | lab | 1 | 1 | 1 |   |
| SEM | Seminar | 2H | online |   | 4 | 1 | 1 |   |

## Related

- [All tables](README.md)
- [Basics](../basics.md)
- [Import and editing errors](../troubleshooting/import-errors.md): what each message means and how to fix it
