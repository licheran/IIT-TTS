# Assignments

Sheet name in Excel and CSV files: `Assignments`.

## What it is

The **result** of a run, one row per placed activity. It is written when you export a run and cannot be edited in the app; it is not one of the tabs on the Tables page.

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `run` | The name of the run the result comes from, for example `run-7`. | text | no | — | — |
| `activity` | The activity. | text | no | — | a code from [Activities](Activities.md) |
| `module` | Its module. Filled in by the program. | text | no | — | filled in by the program, on export only |
| `kind` | Its kind. Filled in by the program. | text | no | — | filled in by the program, on export only |
| `day` | The day it was placed on. | text | no | — | a code from [Days](Days.md) |
| `start` | The time it starts, `HH:MM`. | time (HH:MM) | no | — | — |
| `end` | The time it ends. Filled in by the program. | time (HH:MM) | no | — | filled in by the program, on export only |
| `rooms` | The rooms chosen. | list | no | — | codes from [Rooms](Rooms.md) |
| `groups` | The groups attending. Filled in by the program. | list | no | — | filled in by the program, on export only |
| `teachers` | The teachers. Filled in by the program. | list | no | — | filled in by the program, on export only |
| `buildings` | The buildings of the chosen rooms. Filled in by the program. | list | no | — | filled in by the program, on export only |

## Rules

- Use **Export all (Excel)** on the Timetable tab to get a workbook with this sheet.
- The command `tts validate` checks the assignments of a workbook with the independent verifier.
- Only one run may appear in a sheet.

## Example

An illustration (the L6 sample workbook has no rows in this table):

| `run` | `activity` | `module` | `kind` | `day` | `start` | `end` | `rooms` | `groups` | `teachers` | `buildings` |
|---|---|---|---|---|---|---|---|---|---|---|
| run-7 | 6SENG005C-LEC-01 | 6SENG005C | LEC | Mon | 08:30 | 10:30 | Auditorium | L6 SE / G1;L6 SE / G2 | HAWE;HARR | GP |

## Related

- [All tables](README.md)
- [Basics](../basics.md)
