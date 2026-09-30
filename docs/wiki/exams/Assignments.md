# Assignments

Sheet name in Excel and CSV files: `Assignments`.

## What it is

The **result** of a run, one row per placed exam. It is written when you export a run and cannot be edited in the app.

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `run` | The name of the run the result comes from, for example `run-7`. | text | no | — | — |
| `exam` | The exam. | text | no | — | a code from [Exams](Exams.md) |
| `paper` | Its paper. Filled in by the program. | text | no | — | filled in by the program, on export only |
| `day` | The day it was placed on. | text | no | — | a code from [Days](Days.md) |
| `start` | The time it starts, `HH:MM`. | time (HH:MM) | no | — | — |
| `end` | The time it ends. Filled in by the program. | time (HH:MM) | no | — | filled in by the program, on export only |
| `hall` | The hall chosen. | list | no | — | codes from [Halls](Halls.md) |
| `invigilators` | The invigilators chosen. | list | no | — | codes from [Invigilators](Invigilators.md) |
| `cohorts` | The cohorts that sit it. Filled in by the program. | list | no | — | filled in by the program, on export only |

## Rules

- Use **Export all (Excel)** on the Timetable tab to get a workbook with this sheet.
- The command `tts validate` checks the assignments of a workbook with the independent verifier.

## Example

An illustration (the exams sample workbook has no rows in this table):

| `run` | `exam` | `paper` | `day` | `start` | `end` | `hall` | `invigilators` | `cohorts` |
|---|---|---|---|---|---|---|---|---|
| run-7 | CS101-EXAM | CS101 | 2026-06-01 | 09:00 | 12:00 | MAIN-HALL | INV01;INV02 | BSC-CS-1 |

## Related

- [The exams preset](README.md)
- [Basics](../basics.md)
- [Import and editing errors](../troubleshooting/import-errors.md)
