# Modules

Sheet name in Excel and CSV files: `Modules`.

## What it is

The modules (courses) that are taught. A module belongs to **one level**, is **mandatory or optional**, and lists the **session types** it has (for example a lecture and a tutorial). From that the program works out what to schedule: you do not type the sessions.

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `code` | The module's unique code, for example `6SENG005C`. | text | yes | — | — |
| `name` | The module's title. Free text. | text | no | — | — |
| `level` | The one level the module is taught at. | text | yes | — | a code from [Levels](Levels.md); stored as an attribute |
| `programmes` | The programmes that take the module. Leave blank for every programme at the module's level. | list | no | — | codes from [Programmes](Programmes.md), which must be at the module's level; stored as an attribute |
| `optional` | Tick for an optional module: only the groups that list it in their `options` take it. Untick (mandatory) and every group of its programmes takes it. | true/false | no | false | stored as an attribute |
| `sessions` | The session types the module has, separated by `;`, each optionally followed by settings in brackets. | list | no | — | codes from [SessionTypes](SessionTypes.md), with settings; stored as an attribute |
| `tags` | Labels of the form `key=value`, separated by `;`. See the Tags page. | key=value pairs | no | — | — |

Tags are explained on the [Tags](tags.md) page.

## Rules

- **Who takes a module.** A mandatory module is taken by every group of its programmes. An optional module is taken only by the groups that list it in their `options` (see [Groups](Groups.md)). A module with no groups makes no sessions.
- **`sessions`** is a list such as `LEC;TUT`. A session type can be changed for this module only, by settings in brackets: `LAB(start_pattern=3H,max_groups=2)`. The settings you may use are `start_pattern`, `delivery`, `room_type`, `max_groups`, `teachers` and `weekly`, separated by commas. Anything else is an error (`unknown setting`).
- **Teachers.** A module is taught by the teachers whose `modules` column lists it (see [Teachers](Teachers.md)). The solver chooses which of them takes each session.
- **One flag per module.** A module cannot be mandatory for one programme and optional for another at the same level. Use two modules (two codes) for that.
- Selectors can pick a module's sessions with `ref:<code>`. A session also carries the tags of its session type and of its module (the module's win when both give the same key), so `tag:` selectors can pick sessions too.

## Example

| `code` | `name` | `level` | `programmes` | `optional` | `sessions` | `tags` |
|---|---|---|---|---|---|---|
| 6SENG005C | Software Engineering | L6 | L6 SE | false | LEC;TUT |   |
| 6SENG012C | Machine Learning | L6 | L6 SE | true | LEC;LAB(max_groups=2) |   |

**Hand-made datasets (format version 1).** Datasets whose activities were typed or imported, such as the L6 sample, have a simpler Modules table: `code`, `name`, `level` and `programme` (for information only) and `tags`. Nothing about sessions is kept there.

## Related

- [All tables](README.md)
- [Basics](../basics.md)
- [Import and editing errors](../troubleshooting/import-errors.md): what each message means and how to fix it
