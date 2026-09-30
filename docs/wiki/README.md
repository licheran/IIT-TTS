# IIT-TTS wiki

IIT-TTS builds conflict-free timetables from your data. You describe who and what there is (groups, teachers, rooms, sessions to schedule) and the rules that matter to you. The program places every session in a day and period, and picks the rooms, so that nothing is double-booked and your rules hold.

This wiki is for the people who prepare the data and run the timetable. It explains every tab of the web app and every table, in plain words, with examples from a real term (the L6 Software Engineering and Computer Science sample).

## The workflow

| Step | What you do | Tab |
|---|---|---|
| 1 | Create a dataset for the term or the exam session | [Datasets](tabs/datasets.md) (the home page) |
| 2 | Enter your data, either by typing it into the tables or by importing an Excel file | [Tables](tabs/tables.md), [Import / export](tabs/import-export.md) |
| 3 | Check the data before solving | [Pre-flight](tabs/preflight.md) |
| 4 | Press **Start** and watch the progress | [Run](tabs/run.md) |
| 5 | Read the timetable of any group, teacher or room, and export it | [Timetable](tabs/timetable.md) |
| 6 | Compare runs, publish the one you want, run again | [Runs](tabs/runs.md) |

If a step fails, the [troubleshooting pages](troubleshooting/README.md) explain each message and how to fix it.

## Start here

- [Basics](basics.md): how codes, lists, blanks and `key=value` pairs work everywhere in the app.
- [Glossary](glossary.md): what *activity*, *pooled*, *pin*, *lock*, *run* and the other terms mean.

## Pages

| Section | Pages |
|---|---|
| Basics | [Basics](basics.md), [Glossary](glossary.md) |
| The tabs | [Datasets](tabs/datasets.md), [Tables](tabs/tables.md), [Templates and Expand](tabs/templates-expand.md), [Import / export](tabs/import-export.md), [Pre-flight](tabs/preflight.md), [Run](tabs/run.md), [Timetable](tabs/timetable.md), [Runs](tabs/runs.md) |
| The tables | [Overview of all tables](tables/README.md), [Tags](tables/tags.md), and one page for each table, listed in the overview |
| The exams preset | [Overview](exams/README.md) and one page for each table that differs from the academic preset |
| Troubleshooting | [Where to start](troubleshooting/README.md), [Import and editing errors](troubleshooting/import-errors.md), [Pre-flight issues](troubleshooting/preflight-issues.md), [Run statuses and messages](troubleshooting/run-statuses.md), [Infeasible runs](troubleshooting/infeasible.md) |
| Constraints | [Constraints overview](constraints/README.md), [Selectors](constraints/selectors.md), [Default constraints](constraints/defaults.md), and one page for each of the fourteen types, listed in the overview |


## Two presets

The app ships with two presets. A preset decides which tables exist and what they are called.

- **academic_weekly** is for a weekly timetable of lectures and tutorials across levels, programmes and universities. Most of this wiki describes it.
- **exams** is for an exam session: exams are placed on dated days and sessions, in a hall, with invigilators. See [The exams preset](exams/README.md).
