# Pins

Sheet name in Excel and CSV files: `Pins`.

## What it is

Fixes an exam's day and session, and/or its hall and invigilators. The program keeps every pin.

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `exam` | The exam to pin. | text | yes | — | a code from [Exams](Exams.md) |
| `day` | The day to fix it on. Blank leaves the day free. | text | no | — | a code from [Days](Days.md) |
| `start_period` | The session it must start in. Blank leaves it free. | text | no | — | a code from [Sessions](Sessions.md) |
| `resources` | The hall and/or invigilators to fix. Blank leaves them free. | list | no | — | codes from [Halls](Halls.md), [Invigilators](Invigilators.md) |
| `source` | Who made the pin: `user` for yours (the default). | text | no | `user` | one of `user`, `lock` |

## Rules

- Fill in only what you want to fix. A pin with just `day` keeps the exam on that date but lets the program choose the session.
- The `resources` column can list halls and invigilators together, separated by `;`.
- A pin takes effect in the **next** run. See [Pins](../tables/Pins.md) in the academic reference for more.

## Example

An illustration (the exams sample workbook has no rows in this table):

| `exam` | `day` | `start_period` | `resources` | `source` |
|---|---|---|---|---|
| CS101-EXAM | 2026-06-01 | AM | MAIN-HALL | user |

## Related

- [The exams preset](README.md)
- [Basics](../basics.md)
- [Import and editing errors](../troubleshooting/import-errors.md)
