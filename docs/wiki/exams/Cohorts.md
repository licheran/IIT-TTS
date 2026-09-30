# Cohorts

Sheet name in Excel and CSV files: `Cohorts`.

## What it is

The groups of candidates who sit exams together. **A cohort is an exclusive resource: it can sit only one exam at a time.** This plays the part of Groups in the academic preset.

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `code` | The unique code of the cohort, for example `BSC-CS-1`. | text | yes | — | — |
| `name` | A longer name. Free text. | text | no | — | — |
| `size` | How many candidates. Used to choose a hall that seats them all. | whole number ≥ 0 | no | — | — |
| `tags` | Labels of the form `key=value`, separated by `;`. See [Tags](../tables/tags.md). | key=value pairs | no | — | — |

## Rules

- An exam with several cohorts needs a hall that seats the **sum of their sizes**.
- A cohort never has two exams in the same session. The default rule `EX-SPREAD-<cohort>` also asks for a free day between its exams.

## Example

From the exams sample (`backend/tests/fixtures/exams/exams.xlsx`):

| `code` | `name` | `size` | `tags` |
|---|---|---|---|
| BSC-CS-1 |   | 160 |   |
| BSC-CS-2 |   | 140 |   |

## Related

- [The exams preset](README.md)
- [Basics](../basics.md)
- [Import and editing errors](../troubleshooting/import-errors.md)
