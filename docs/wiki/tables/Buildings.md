# Buildings

Sheet name in Excel and CSV files: `Buildings`.

## What it is

The buildings that contain rooms.

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `code` | The unique name of this row. Other tables refer to it. | text | yes | — | — |
| `name` | A longer name for people. Free text. It is not used for matching. | text | no | — | — |
| `abbreviation` | A short form of the name, for example `GP`. Can be used in selectors with `attr:abbreviation=GP`. | text | no | — | stored as an attribute |
| `campus` | The campus the building is on. Optional. | text | no | — | a code from [Campuses](Campuses.md) |
| `tags` | Labels of the form `key=value`, separated by `;`. See the Tags page. | key=value pairs | no | — | — |

Tags are explained on the [Tags](tags.md) page.

## Rules

- A building only groups rooms. The constraint `travel_gap` uses buildings to know when a group or teacher has to change building.
- Rooms in different buildings: the institute needs no free time for a change of building, so the default constraint `AC-TRAVEL` is created switched off.

## Example

From the L6 sample:

| `code` | `name` | `abbreviation` | `campus` | `tags` |
|---|---|---|---|---|
| GP | GP |   | MAIN |   |

## Related

- [All tables](README.md)
- [Basics](../basics.md)
