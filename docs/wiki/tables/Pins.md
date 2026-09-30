# Pins

Sheet name in Excel and CSV files: `Pins`.

> **Hand-made datasets only.** A dataset built from configuration has no Pins table: to keep a session where you want it, edit it on the [Activities](../tabs/activities.md) tab. The next run keeps the edited values.

## What it is

Fixes an activity's time and/or rooms. The solver keeps every pin. You normally create pins from the [Timetable](../tabs/timetable.md) tab with **Pin here**, but they can be typed here.

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `activity` | The activity to pin. | text | yes | — | a code from [Activities](Activities.md) |
| `day` | The day to fix it on. Blank leaves the day free. | text | no | — | a code from [Days](Days.md) |
| `start_period` | The period it must start in. Blank leaves the start free. | text | no | — | a code from [Periods](Periods.md) |
| `rooms` | The room or rooms to fix. Blank leaves the room free. | list | no | — | codes from [Rooms](Rooms.md) |
| `source` | Who made the pin: `user` for yours (the default). | text | no | `user` | one of `user`, `lock` |

## Rules

- Fill in only what you want to fix. A pin with just `rooms` keeps the activity in that room but lets the solver choose the time.
- An activity can have pins in several rows. Together they must agree.
- Two pins that put activities on the same room or the same group at the same time are reported by pre-flight as `conflicting_pins`.
- A pin takes effect in the **next** run.
- `source` `lock` is used for pins the program creates itself. Leave `source` blank for your own: it becomes `user`.

## Example

An illustration (the L6 sample workbook has no rows in this table):

| `activity` | `day` | `start_period` | `rooms` | `source` |
|---|---|---|---|---|
| 6SENG005C-LEC-01 | Mon | P01 | Auditorium | user |

## Related

- [All tables](README.md)
- [Basics](../basics.md)
- [Import and editing errors](../troubleshooting/import-errors.md): what each message means and how to fix it
