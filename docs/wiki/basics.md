# Basics

These rules hold in every table, in the web app and in Excel or CSV files alike.

## What it's for

Knowing them once saves you from most import errors.

## The rules

### Codes

- Every row that stands for a thing (a teacher, a room, a group, an activity) has a **code**. The code is its name inside the data, and it must be **unique within its table**.
- Other tables refer to a thing by its code. A teacher's `modules` that says `6SENG005C` means the module whose code is `6SENG005C`.
- Codes are trimmed (spaces at both ends are removed). Matching is **case-sensitive**: `Lab-1` and `lab-1` are different.
- A code may contain spaces and `/`, for example `L6 SE / G1`.

### Lists

A cell that holds several items separates them with `;`, for example `HAWE;HARR`. There is no space needed after the `;`.

### Key=value pairs (tags)

A `tags` cell holds pairs separated by `;`, each written `key=value`, for example `university=UOW;floor=2`. How tags are used is explained on the [Tags](tables/tags.md) page.

### Blank cells

- An empty cell means "nothing", or the default where the table has one. The [table pages](tables/README.md) list the default of every column.
- A blank is never the same as `0` or `false`.

### True and false

Write `true` or `false` (any capitals), or `1` or `0`. In the app, true/false columns are checkboxes.

### Times

Write times as `HH:MM` on the 24-hour clock, for example `08:30` or `14:00`.

### Your own notes

A column whose header starts with `x_` (for example `x_comment`) is your own note. The program keeps it and ignores it.

### Anything else is an error

A column header the program does not know, and does not start with `x_`, is refused. Header names must match exactly, including capitals.

## How an import behaves

- The program reads the **whole** file first and collects **every** problem. If there is even one, **nothing is imported** and the data stays as it was.
- Each problem is written as `Sheet!R<row>C<column> [column name]: message`, for example `Teachers!R12C3 [modules]: unknown code "6SENG05C"`. This means: sheet `Teachers`, row 12, column 3.
- Exporting and importing again gives you the same data back.

## Related

- [Glossary](glossary.md)
