# Workbook information

Sheet name in Excel and CSV files: `_meta`.

## What it is

Information about the workbook itself, one setting per row. It is not timetable data. Open it to see which preset and format version a file belongs to, or to keep notes such as the institution's name.

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `key` | The name of the setting. | text | yes | — | — |
| `value` | Its value. | text | no | — | — |

## Rules

- **`format_version`** is required. It is a whole number, currently `1`. A file with a newer version than the app understands is refused.
- **`preset`** is required. It names the preset the file belongs to, for example `academic_weekly`.
- You may add other keys, for example `institution`, `exported_at` or `assumptions` (free text). They are kept when you export and import again and are not used for scheduling.
- Every key may appear only once.

## Example

From the L6 sample:

| `key` | `value` |
|---|---|
| format_version | 1 |
| preset | academic_weekly |

## Related

- [All tables](README.md)
- [Basics](../basics.md)
