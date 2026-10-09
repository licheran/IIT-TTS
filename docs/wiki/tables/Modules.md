# Modules

Sheet name in Excel and CSV files: `Modules`.

## What it is

The modules (courses) that are taught. A module belongs to **one level** and is **mandatory or optional**. Its **session types** (for example a lecture and a tutorial) are the rows of the [Session](Session.md) table. From that the program works out what to schedule: you do not type the sessions.

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `code` | The module's unique code, for example `6SENG005C`. | text | yes | — | — |
| `name` | The module's title. Free text. | text | no | — | — |
| `level` | The one level the module is taught at. | text | yes | — | a code from [Levels](Levels.md); stored as an attribute |
| `programmes` | The programmes that take the module. Leave blank for every programme at the module's level. | list | no | — | codes from [Programmes](Programmes.md), which must be at the module's level; stored as an attribute |
| `optional` | Tick for an optional module: only the groups that list it in their `options` take it. Untick (mandatory) and every group of its programmes takes it. | true/false | no | false | stored as an attribute |
| `tags` | Labels of the form `key=value`, separated by `;`. See the Tags page. | key=value pairs | no | — | — |

Tags are explained on the [Tags](tags.md) page.

## Rules

- **Who takes a module.** A mandatory module is taken by every group of its programmes. An optional module is taken only by the groups that list it in their `options` (see [Groups](Groups.md)). A module with no groups makes no sessions.
- **Session types.** A module has one [Session](Session.md) row for each kind of session it holds. A module with no rows has no sessions, and pre-flight warns when groups take it.
- **Teachers.** A module is taught by the teachers whose `modules` column lists it (see [Teachers](Teachers.md)). The solver chooses which of them takes each session.
- **One flag per module.** A module cannot be mandatory for one programme and optional for another at the same level. Use two modules (two codes) for that.
- Selectors can pick a module's sessions with `ref:<code>`. A session also carries the tags of its session type, of its module and of its Session row (each wins over the one before it), so `tag:` selectors can pick sessions too.

## Example

| `code` | `name` | `level` | `programmes` | `optional` | `tags` |
|---|---|---|---|---|---|
| 6SENG005C | Software Engineering | L6 | L6 SE | false |   |
| 6SENG012C | Machine Learning | L6 | L6 SE | true |   |

Their lectures, tutorials and labs are rows of the [Session](Session.md) table.

**Hand-made datasets (format version 1).** Datasets whose activities were typed or imported, such as the L6 sample, have a simpler Modules table: `code`, `name`, `level` and `programme` (for information only) and `tags`. Nothing about sessions is kept there.

## Related

- [All tables](README.md)
- [Basics](../basics.md)
- [Import and editing errors](../troubleshooting/import-errors.md): what each message means and how to fix it
