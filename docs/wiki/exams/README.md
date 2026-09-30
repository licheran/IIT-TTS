# The exams preset

## What it is

The **exams** preset schedules an exam session instead of a weekly teaching timetable. Each exam is placed on a **day and a session** (for example a morning or an afternoon), in a **hall** big enough for all its candidates, with the **invigilators** it needs. Nothing is double-booked: a cohort sits one exam at a time, a hall holds one exam at a time, and an invigilator supervises one exam at a time.

Everything you learnt about the app's tabs still applies: [Tables](../tabs/tables.md), [Import / export](../tabs/import-export.md), [Pre-flight](../tabs/preflight.md), [Run](../tabs/run.md), [Timetable](../tabs/timetable.md) and [Runs](../tabs/runs.md) work the same way. What changes is **which tables exist and what they are called**.

## How to start

1. On the home page, create a dataset with the preset **exams**.
2. Fill in the tables, or import a workbook. The sample `backend/tests/fixtures/exams/exams.xlsx` has two weeks of exam days, eight cohorts, four halls, twelve invigilators and twenty-four exams.
3. Check it on the Pre-flight tab, press **Start** on the Run tab, and open the timetable.

A new exams dataset is empty. It has no days, no sessions and no start patterns, and no default constraints (there are no cohorts yet).

## How it differs from the academic preset

| Academic preset | Exams preset | Note |
|---|---|---|
| Days (`Mon`, `Tue`, …) | [Exam days](Days.md) (dates) | Each day is a date such as `2026-06-01` |
| Periods | [Sessions](Sessions.md) | Usually a morning and an afternoon session |
| Groups | [Cohorts](Cohorts.md) | The candidates who sit exams together |
| Rooms, with a room type | [Halls](Halls.md), with no type | Any hall that seats the cohorts will do |
| Teachers | [Invigilators](Invigilators.md) | How many are needed is set on each exam |
| Modules | [Papers](Papers.md) | |
| Activities | [Exams](Exams.md) | No room type, no delivery, no templates |
| ActivityGroups | [ExamCohorts](ExamCohorts.md) | |
| Universities, Levels, Programmes, Campuses, Buildings, Templates | (none) | The exams preset does not have these |

## The tables

| Table (tab name) | Sheet name | Page |
|---|---|---|
| Workbook information | `_meta` | Same as academic: [_meta](../tables/_meta.md). The preset is `exams` |
| Exam days | `Days` | [Days](Days.md) |
| Sessions | `Sessions` | [Sessions](Sessions.md) |
| Start patterns | `StartPatterns` | Same as academic, with Sessions instead of Periods: [StartPatterns](../tables/StartPatterns.md) |
| Cohorts | `Cohorts` | [Cohorts](Cohorts.md) |
| Halls | `Halls` | [Halls](Halls.md) |
| Invigilators | `Invigilators` | [Invigilators](Invigilators.md) |
| Papers | `Papers` | [Papers](Papers.md) |
| Exams | `Exams` | [Exams](Exams.md) |
| Exam cohorts | `ExamCohorts` | [ExamCohorts](ExamCohorts.md) |
| Availability | `Availability` | Same as academic, for cohorts, halls and invigilators: [Availability](../tables/Availability.md) |
| Constraints | `Constraints` | Same as academic: [Constraints](../tables/Constraints.md) |
| Pins | `Pins` | [Pins](Pins.md) |
| Assignments (export only) | `Assignments` | [Assignments](Assignments.md) |

## What the program does for you

- **Each exam gets one hall** that seats the **sum of the sizes** of its cohorts, and the number of invigilators you ask for.
- **A cohort never has two exams in the same session.** Two papers that share a cohort are kept apart automatically.
- The rule `EX-SPREAD-<cohort>` (soft, weight 1) asks for at least one free day between a cohort's exams. See [Default constraints](../constraints/defaults.md).
- All the [constraint types](../constraints/README.md) and [selectors](../constraints/selectors.md) work here too. For example, `uses:(code:"BSC-CS-1")` picks the exams a cohort sits, and `min_days_between` spreads them.

## Looking at the result

On the [Timetable](../tabs/timetable.md) tab the resource types are **Cohort**, **Hall** and **Invigilator**. Choose a cohort to see its exams, a hall to see how it is used, or an invigilator to see their duty roster. The grid has one column for each exam day and one row for each session. A block shows the paper, `Exam ·` and the exam's code, the cohorts, and the hall and invigilators chosen.

## Related

- [Tables (academic reference)](../tables/README.md)
- [Constraints](../constraints/README.md)
- [Troubleshooting](../troubleshooting/README.md)
