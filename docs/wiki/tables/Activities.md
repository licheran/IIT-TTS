# Activities

Sheet name in Excel and CSV files: `Activities`.

## What it is

The sessions to schedule: each row is one lecture, tutorial or lab that needs a time and (usually) a room.

**In a dataset built from configuration there is nothing to type here.** The solver makes the sessions from the modules and session types, and the Activities tab shows the result: see [Activities](../tabs/activities.md). The rest of this page describes the **hand-made** datasets (format version 1, such as the L6 sample), where the activities are typed or imported and the solver places them.

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `code` | The activity's unique code, for example `6SENG005C-TUT-01`. | text | yes | — | — |
| `module` | The module the activity belongs to. | text | no | — | a code from [Modules](Modules.md) |
| `kind` | What sort of session it is: `LEC`, `TUT`, `LAB`, `SEM` or your own. | text | yes | — | — |
| `duration` | How many consecutive periods it lasts. | whole number ≥ 1 | yes | — | — |
| `start_pattern` | Which start pattern says when it may start. | text | yes | — | a code from [StartPatterns](StartPatterns.md) |
| `delivery` | `in_person` or `online`. An online activity has no room. | text | no | `in_person` | — |
| `room_type` | The kind of room it needs. | text | no | — | — |
| `room_count` | How many rooms it needs. Normally 1. | whole number ≥ 0 | no | — | — |
| `template` | The template that generated this activity. Filled in by Expand, blank for hand-made ones. | text | no | — | a code from [Templates](Templates.md) |
| `groups` | A shortcut for typing the groups that attend, separated by `;`. It becomes rows of ActivityGroups. | list | no | — | codes from [Groups](Groups.md), [Programmes](Programmes.md), [Levels](Levels.md); shortcut: becomes rows of [ActivityGroups](ActivityGroups.md); never written on export |
| `teachers` | A shortcut for the teachers, separated by `;`. It becomes rows of ActivityTeachers. | list | no | — | codes from [Teachers](Teachers.md); shortcut: becomes rows of [ActivityTeachers](ActivityTeachers.md); never written on export |
| `tags` | Labels of the form `key=value`, separated by `;`. See the Tags page. | key=value pairs | no | — | — |

Tags are explained on the [Tags](tags.md) page.

## Rules

- **Who attends and who teaches** is kept in two sheets of the file, ActivityGroups and ActivityTeachers, one row per pair. The application shows them as the `groups` and `teachers` columns of this table, which you edit with a checklist. In a file, the two sheets hold the information; the `groups` and `teachers` columns are a shortcut for typing a file by hand (they turn into those rows on import) and are **not written** on export.
- **Rooms.** For an `in_person` activity, `room_type` is required unless `room_count` is `0`. `room_count` is 1 when left blank. For an `online` activity, leave `room_type` and `room_count` blank.
- The room must seat the **sum of the sizes** of the groups that attend (the capacity rule), and its `room_type` must match exactly.
- An activity with several groups is a **joint** activity: all of them attend at once, and all of them are occupied.
- The `template` column is kept for old files. Template rows are expanded once when a file is imported, and the activities they make have no `template`.
- Import errors for this table: `required unless room_count is 0 (or the activity is online)`, `an online activity cannot have a room type`, `an online activity cannot have rooms` and `expected integer ≥ 1 when room_type is set`.

## Example

From the L6 sample:

| `code` | `module` | `kind` | `duration` | `start_pattern` | `delivery` | `room_type` | `room_count` | `template` | `tags` |
|---|---|---|---|---|---|---|---|---|---|
| 6BUIS019C-LEC-01 | 6BUIS019C | LEC | 2 | 2H | in_person | lab | 1 |   | fet_label=1.30pm - 3.30pm |
| 6BUIS019C-TUT-01 | 6BUIS019C | TUT | 2 | 2H | in_person | lab | 1 |   | fet_label=10.30am -12.30pm |

## Related

- [All tables](README.md)
- [Basics](../basics.md)
- [Import and editing errors](../troubleshooting/import-errors.md): what each message means and how to fix it
