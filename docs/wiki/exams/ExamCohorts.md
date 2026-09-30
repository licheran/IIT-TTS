# Exam cohorts

Sheet name in Excel and CSV files: `ExamCohorts`.

## What it is

Says **which cohorts sit which exam**: one row per pair. An exam with several rows is a joint exam.

## Columns

| Column | Meaning | Type | Required | Default | Allowed values or refers to |
|---|---|---|---|---|---|
| `exam` | The exam. | text | yes | — | a code from [Exams](Exams.md) |
| `cohort` | The cohort that sits it. | text | yes | — | a code from [Cohorts](Cohorts.md) |

## Rules

- To add a cohort to an exam, add a row. To remove it, delete the row.
- A cohort can sit only one exam per session: two exams of one cohort never share a session.

## Example

From the exams sample (`backend/tests/fixtures/exams/exams.xlsx`):

| `exam` | `cohort` |
|---|---|
| AI501-EXAM | MSC-AI |
| AI502-EXAM | MSC-AI |

## Related

- [The exams preset](README.md)
- [Basics](../basics.md)
- [Import and editing errors](../troubleshooting/import-errors.md)
