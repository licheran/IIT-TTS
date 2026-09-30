# Templates

Sheet name in Excel and CSV files: `Templates`.

## What it is

Rules that **generate activities**. One template row stands for a whole set of activities (every group's tutorial, say). Use the Expand panel on this tab to turn them into rows of Activities. Skip this table if you type activities by hand.

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `code` | The template's unique code. | text | yes | — | — |
| `module` | The module the generated activities belong to. | text | yes | — | a code from [Modules](Modules.md) |
| `kind` | The kind of activity, for example `LEC` or `TUT`. Free text, but use the same spelling throughout. | text | yes | — | — |
| `mode` | How many activities to make: one joint one, one per group, or one per batch of groups. | text | yes | — | one of `joint`, `per_group`, `batched` |
| `groups` | Which groups the activities are for, as a selector. | selector | yes | — | — |
| `batch_size` | How many groups in each batch. Only for mode `batched`. | whole number ≥ 1 | yes, when mode is batched | — | — |
| `teachers` | The teachers of the generated activities. | list | no | — | codes from [Teachers](Teachers.md) |
| `duration` | How many periods each activity lasts. | whole number ≥ 1 | yes | — | — |
| `start_pattern` | The start pattern of the generated activities. | text | yes | — | a code from [StartPatterns](StartPatterns.md) |
| `room_type` | The room type they need. Leave blank for an activity that needs no room (it is made `online`). | text | no | — | — |
| `sessions_per_week` | How many times a week the activity happens. Each session is a separate activity. | whole number ≥ 1 | no | `1` | — |
| `active` | Untick to stop a template from generating, without deleting it. | true/false | no | true | — |

## Rules

- **`mode`** is one of `joint` (one activity with all matching groups together), `per_group` (one activity per matching group) or `batched` (the matching groups are sorted by code and cut into batches of `batch_size`; one activity per batch).
- **`groups`** is a selector, for example `under:L6 SE` for every group below the SE programme, or `code:"L6 CS / G13"` for one group. See [Selectors](../constraints/selectors.md).
- **`batch_size`** is required when `mode` is `batched`, and ignored otherwise.
- Generated activities are named `<module>-<kind>-<nn>` and carry the template's code in their `template` column.
- See [Templates and Expand](../tabs/templates-expand.md) for the preview and commit.

## Example

From the L6 sample written as templates (`templates.xlsx`):

| `code` | `module` | `kind` | `mode` | `groups` | `batch_size` | `teachers` | `duration` | `start_pattern` | `room_type` | `sessions_per_week` | `active` |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 6BUIS019C-LEC-T01 | 6BUIS019C | LEC | joint | code:"L6 CS / G12","L6 CS / G13","L6 CS / G14" |   | THE | 2 | 2H | lab | 1 | true |
| 6BUIS019C-TUT-T01 | 6BUIS019C | TUT | per_group | code:"L6 CS / G13" |   | IMAS;MJAN | 2 | 2H | lab | 1 | true |

## Related

- [All tables](README.md)
- [Basics](../basics.md)
- [Import and editing errors](../troubleshooting/import-errors.md): what each message means and how to fix it
