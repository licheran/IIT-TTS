# Exams

Sheet name in Excel and CSV files: `Exams`.

## What it is

The exams to schedule: each row is one sitting of one paper that needs a day, a session, a hall and invigilators. **This is the table the solver works on.** It plays the part of Activities.

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `code` | The exam's unique code, for example `CS101-EXAM`. | text | yes | — | — |
| `paper` | The paper being sat. | text | no | — | a code from [Papers](Papers.md) |
| `kind` | `EXAM` or `PRACTICAL`. | text | yes | — | one of `EXAM`, `PRACTICAL` |
| `duration` | How many consecutive sessions the exam takes. Normally 1. | whole number ≥ 1 | yes | — | — |
| `start_pattern` | Which start pattern says when it may start. | text | yes | — | a code from [StartPatterns](../tables/StartPatterns.md) |
| `invigilators` | How many invigilators it needs. | whole number ≥ 0 | no | `1` | — |
| `cohorts` | A shortcut for typing the cohorts that sit it, separated by `;`. It becomes rows of ExamCohorts. | list | no | — | codes from [Cohorts](Cohorts.md); shortcut: becomes rows of [ExamCohorts](ExamCohorts.md); never written on export |
| `tags` | Labels of the form `key=value`, separated by `;`. See [Tags](../tables/tags.md). | key=value pairs | no | — | — |

## Rules

- **Who sits it** is kept in [ExamCohorts](ExamCohorts.md), one row per pair. The `cohorts` column is a shortcut for typing a file by hand: on import it turns into those rows, and on export it is **not written**.
- **Hall.** Every exam needs exactly one hall, chosen by the program: any hall that seats the sum of the sizes of its cohorts. There is no column for it.
- **Invigilators.** `invigilators` is how many are needed. Leave it blank for 1, or write `0` for none. The sample sets it to one for every 60 candidates, rounded up. The program chooses which invigilators.
- An exam with several cohorts is a **joint** exam: all of its cohorts sit it together, in one hall.
- The exams preset has a different set of columns from the academic Activities: no room type, no delivery and no templates.

## Example

From the exams sample (`backend/tests/fixtures/exams/exams.xlsx`):

| `code` | `paper` | `kind` | `duration` | `start_pattern` | `invigilators` | `tags` |
|---|---|---|---|---|---|---|
| AI501-EXAM | AI501 | EXAM | 1 | SESSION | 1 |   |
| AI502-EXAM | AI502 | EXAM | 1 | SESSION | 1 |   |

## Related

- [The exams preset](README.md)
- [Basics](../basics.md)
- [Import and editing errors](../troubleshooting/import-errors.md)
