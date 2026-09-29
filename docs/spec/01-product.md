# 01 — Product: Definition, Use Case, Requirements

Status: **Authoritative.** Requirement IDs (FR-n, NFR-n) are referenced from the phase files and tests.

## 1. Definition

**IIT-TTS** (IIT TimeTabling Solution) is a data-driven scheduling application. It places **events** in **time** and assigns them the **resources** they require, so that:
- no exclusive resource is ever used by two events in the same period, and
- every hard rule holds while soft rules are optimised.

Users declare entities and relationships as tables, either in the app or through an Excel/CSV workbook. IIT-TTS then goes through four steps:
1. It **expands** templates into events.
2. It **pre-flight checks** the data.
3. It **solves** for start times and pooled resources.
4. It **verifies** the result and publishes grids and exports for every resource.

The core is domain-neutral. Vocabulary such as teacher, room or module comes from a **preset** (see `02-domain-model.md` §6).

## 2. Primary use case: conflict-free course timetabling and room allocation

> Automated scheduling of an institution's weekly teaching activities (lectures, tutorials, labs, …). Every activity gets a time slot and a suitable room. No student group, teacher or room is double-booked in any period. Cohorts, joint and shared sessions, room capacity and type, the institution's time pattern and availability are all respected. Preferences such as fewer gaps, fewer campus days and fewer building changes are optimised. The result is one institute-wide timetable, published per group, teacher, room and building.

**Actors.**
- The **timetable administrator** maintains the data, runs solves, and reviews and publishes the results.
- **Coordinators** supply the teaching requirements.
- **Teachers and students** read the published timetables. They are read-only in v1.

### 2.1 Variations that must be supported as data (no code changes)

| Dimension | Known values | Must also allow |
|---|---|---|
| Levels | L4, L5, L6, L7 | Any |
| Degree programmes | CS, SE, BDS, AIDS | Any |
| Awarding universities | UOW, RGU | Any, each with its own rules |
| Campuses and buildings | GP, Java, Rama, Dialog, Spencer (plus abbreviations) | Any, with nesting (Campus → Building → Room) |
| Delivery | In person, online | Hybrid; events with no room |
| Time patterns | 2-hour blocks at 08:30, 10:30, 13:30, 15:30, 17:30; lunch break at 12:30 | Other block lengths or patterns per level, programme or university |
| Sharing | Teachers and rooms shared across levels, programmes and universities | Any resource shared by any events |

### 2.2 Reference dataset: L6 SE + CS

Source: a real FET groups export (`backend/tests/fixtures/l6/`). The measured values are in `expected.json`.
- 30 groups (SE G1–G11, CS G1–G19), 57 teacher codes, 10 rooms (all in building GP) and 10 modules.
- 77 sessions (22 LEC, 55 TUT), all 2 periods long.
- A 6-day × 14-period grid.
- Joint sessions with up to 7 groups and 7 teachers.
- 1 online session.
- 0 clashes.

### 2.3 Scope boundary

A timetable is conflict-free only across the resources **in the same solve**. Institute-wide conflict-freedom needs either one dataset for everything (FR-15), or staged solving in which earlier published assignments are locked (FR-10).

## 3. Secondary use cases (future presets; used to test that the core is generic)

| Use case | Events | Fixed resources | Pooled resources | Typical constraints |
|---|---|---|---|---|
| Exam timetabling | Exams | Cohorts | Halls, invigilators | Min days between a cohort's exams, capacity |
| Staff rostering | Shifts | — | Staff with required skills | Min rest, max hours, fairness |
| Room booking | Meetings | Organisers | Rooms | Availability, capacity, equipment |
| Sports fixtures | Matches | Teams | Venues, referees | Rest days, home/away balance |

## 4. Functional requirements

| ID | Requirement | Phase |
|---|---|---|
| FR-1 | Create, edit and delete entities and relationships in table views | 7 |
| FR-2 | Import and export the complete configuration as one `.xlsx` or a CSV zip, lossless on a round trip | 3 |
| FR-3 | Reject invalid imports atomically, with *all* row-level errors reported | 3 |
| FR-4 | Define resource types, attributes, hierarchies and tags without code changes | 1, 3 |
| FR-5 | Expand templates into events, with a preview before committing | 9 |
| FR-6 | Run pre-flight checks. Errors block Start; warnings don't | 5 |
| FR-7 | Start a solve with one action, with live progress and cancel | 6, 7 |
| FR-8 | Return a conflict-free assignment meeting every hard constraint, or an explanation naming the conflicting constraints and entities | 4, 5 |
| FR-9 | Optimise soft constraints and report the score broken down by constraint instance | 8 |
| FR-10 | Honour user pins, and locked assignments from published runs | 4, 6, 10 |
| FR-11 | Store every run with its input snapshot and hash. Allow comparing runs, publishing one per dataset, and re-running | 6, 7 |
| FR-12 | Show a weekly grid for any resource type and resource, plus an assignment list | 7 |
| FR-13 | Export results as HTML, XLSX and CSV (PDF later), per resource and as a whole | 6 |
| FR-14 | Validate any assignment, including one imported from FET, and report every violation | 1, 2 |
| FR-15 | Support datasets containing many levels, programmes, universities and buildings together | 10 |
| FR-16 | Support at least one non-academic preset with no changes to the core | 11 |

## 5. Non-functional requirements (targets)

| ID | Requirement |
|---|---|
| NFR-1 | L6 hard-constraint solve (no pins) finds a feasible solution in ≤ 30 s on a 4-core laptop |
| NFR-2 | An institute-scale dataset of about 3,000 events finds a feasible solution in ≤ 15 min on 8 cores |
| NFR-3 | Deterministic: the same snapshot, seed, parameters and `num_workers=1` give the same result |
| NFR-4 | Importing a workbook with 10,000 rows takes ≤ 10 s |
| NFR-5 | The core has no domain vocabulary. A preset is configuration plus labels |
| NFR-6 | Every hard violation in a stored result is visible to the user. None are hidden |
| NFR-7 | Pre-flight on L6 takes ≤ 1 s |
| NFR-8 | Table editors stay responsive with 5,000 rows |

## 6. Non-goals (v1)

- Individual student enrolment or sectioning. Students are scheduled as groups.
- Self-service edits by teachers or students.
- Multi-tenant SaaS. v1 is one institute per deployment.
- A free-form rule or scripting language.
- Real-time booking.

## 7. Glossary

| Term | Meaning |
|---|---|
| Clash / conflict | An exclusive resource occupied by two events in one period |
| Joint event | An event whose fixed resources include several resources of one type (for example, several groups) |
| Hard constraint | Must hold. A result that breaks it is invalid |
| Soft constraint | A preference. Breaking it adds `weight × penalty` to the score |
| Feasible | Every event is placed and every hard constraint holds |
| Pin | A user-fixed time and/or resource for an event |
| Lock | A pin derived from a published run (source `lock`) |
| Preset | A packaged set of resource types, sheets, labels, default constraints and templates for one domain |
