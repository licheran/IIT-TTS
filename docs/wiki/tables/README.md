# The tables

A dataset is made of **tables** (called *sheets* in an Excel workbook). Each table has its own page here, with every column: what it means, its type, whether you must fill it in, its default, and what it refers to.

Read [Basics](../basics.md) first if you have not: it explains codes, lists, blanks and `key=value` pairs, which apply to every table.

## How the tables fit together

A dataset is one of two kinds. A **configured** dataset (workbook format version 2) holds only the configuration: the program works out the sessions and the solver places them. A **hand-made** dataset (format version 1, such as the L6 sample) holds the sessions themselves, typed or imported. The two kinds are told apart by their Activities: a hand-made dataset's activities are typed in; a configured dataset has none to type.

```
Universities ──► Levels ──► Programmes ──► Groups                      who attends
    (optional)                              (exclusive; list their optional Modules)

Teachers  (list the Modules they teach)                                who teaches (exclusive)

Campuses ──► Buildings ──► Rooms                                       where (Rooms exclusive)

Days, Periods, StartPatterns                                           when

SessionTypes ──► Modules ──(solver)──► Activities                      what to schedule
                 (one level, mandatory or optional)    (the solver's output)

Availability, Constraints                                              rules
```

- An arrow `A ──► B` means "each B has a parent A" or "B uses A": a level belongs to a university, a programme to a level, a group to a programme, a building to a campus, a room to a building, a module lists session types.
- **Exclusive** resources (groups, teachers, rooms) can be in only one session at a time. The rest only group things.
- Other tables refer to a row by its **code**. A reference to a code that does not exist is an error.
- In a configured dataset the **Activities** are the solver's output, not something you fill in: see [Activities](Activities.md).

## The tables of a configured dataset, in the order of the workbook

| Table | What it holds | Page |
|---|---|---|
| Workbook information (`_meta`) | The preset and format version of the file, and your notes | [_meta](_meta.md) |
| Days | The days of the week | [Days](Days.md) |
| Periods | The time slots of a day, and breaks | [Periods](Periods.md) |
| Start patterns (`StartPatterns`) | When a session of a given length may start | [StartPatterns](StartPatterns.md) |
| Universities | Awarding universities | [Universities](Universities.md) |
| Levels | Academic levels | [Levels](Levels.md) |
| Programmes | Degree programmes | [Programmes](Programmes.md) |
| Groups | Student groups and their optional modules | [Groups](Groups.md) |
| Teachers | Teachers and the modules they teach | [Teachers](Teachers.md) |
| Campuses | Campuses | [Campuses](Campuses.md) |
| Buildings | Buildings | [Buildings](Buildings.md) |
| Rooms | Rooms, their size and type | [Rooms](Rooms.md) |
| Session types (`SessionTypes`) | The kinds of session and their settings | [SessionTypes](SessionTypes.md) |
| Modules | The courses, their level and their sessions | [Modules](Modules.md) |
| Availability | When a resource cannot or should not be used | [Availability](Availability.md) |
| Constraints | Your rules | [Constraints](Constraints.md) |

## Tables of hand-made datasets only

These belong to format version 1. A configured dataset has none of them: its sessions are the solver's, and you correct a session in the Activities view (see [Activities](Activities.md)).

| Table | What it holds | Page |
|---|---|---|
| Templates | Rules that generate activities | [Templates](Templates.md) |
| Activities | The sessions to schedule | [Activities](Activities.md) |
| Activity groups (`ActivityGroups`) | Which groups attend which activity | [ActivityGroups](ActivityGroups.md) |
| Activity teachers (`ActivityTeachers`) | Which teachers teach which activity | [ActivityTeachers](ActivityTeachers.md) |
| Pins | Activities you fixed in time or place | [Pins](Pins.md) |
| Assignments | A run's result (export only) | [Assignments](Assignments.md) |

A hand-made dataset's Groups, Teachers and Modules tables have fewer columns than the pages show (no `options`, `modules`, `level`, `programmes`, `optional` or `sessions`): each of those pages says so.

The name in brackets is the sheet name in an Excel or CSV file. In the app the tabs show the friendlier name.

## A sensible order to fill them in

1. **Days, Periods, Start patterns**: the shape of the week.
2. **Universities, Levels, Programmes**, **Campuses, Buildings, Rooms**: the institute and its places.
3. **Session types**: the kinds of session you hold.
4. **Modules**, each with its level, whether it is optional, and its session types.
5. **Groups** with their optional modules, and **Teachers** with the modules they teach.
6. **Availability** and **Constraints** when you need them.
7. Run the solver. The sessions appear in the Activities view, where you can correct them.

## Two kinds of columns you will meet

- **Shortcut columns** (hand-made datasets). `groups` and `teachers` on Activities are conveniences for typing a file by hand. They turn into rows of ActivityGroups and ActivityTeachers when imported, and are never written on export.
- **Filled-in columns.** A few columns, such as `module` and `end` in Assignments, are worked out by the program when you export. You cannot type them.

## Related

- [Tags](tags.md)
- [Constraints and selectors](../constraints/README.md)
- [Glossary](../glossary.md)
