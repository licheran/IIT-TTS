# The tables

A dataset is made of **tables** (called *sheets* in an Excel workbook). Each table has its own page here, with every column: what it means, its type, whether you must fill it in, its default, and what it refers to.

Read [Basics](../basics.md) first if you have not: it explains codes, lists, blanks and `key=value` pairs, which apply to every table.

## How the tables fit together

```
Universities ──► Levels ──► Programmes ──► Groups ──► (sub-)Groups     who attends
    (optional)                              (exclusive)

Teachers                                                               who teaches (exclusive)

Campuses ──► Buildings ──► Rooms                                       where (Rooms exclusive)

Days, Periods, StartPatterns                                           when

Modules ◄── Templates ──► (Expand) ──► Activities ──► ActivityGroups   what to schedule
                                          │       └──► ActivityTeachers
                                          └── room_type asks for a Room

Availability, Constraints, Pins                                        rules and fixed choices
Assignments                                                            the result (export only)
```

- An arrow `A ──► B` means "each B has a parent A": a level belongs to a university, a programme to a level, a group to a programme or to another group, a building to a campus, a room to a building.
- **Exclusive** resources (groups, teachers, rooms) can be in only one activity at a time. The rest only group things.
- Other tables refer to a row by its **code**. A reference to a code that does not exist is an error.

## The tables, in the order of the workbook

| Table | What it holds | Page |
|---|---|---|
| Workbook information (`_meta`) | The preset and format version of the file, and your notes | [_meta](_meta.md) |
| Days | The days of the week | [Days](Days.md) |
| Periods | The time slots of a day, and breaks | [Periods](Periods.md) |
| Start patterns (`StartPatterns`) | When an activity of a given length may start | [StartPatterns](StartPatterns.md) |
| Universities | Awarding universities | [Universities](Universities.md) |
| Levels | Academic levels | [Levels](Levels.md) |
| Programmes | Degree programmes | [Programmes](Programmes.md) |
| Groups | Student groups | [Groups](Groups.md) |
| Teachers | Teachers | [Teachers](Teachers.md) |
| Campuses | Campuses | [Campuses](Campuses.md) |
| Buildings | Buildings | [Buildings](Buildings.md) |
| Rooms | Rooms, their size and type | [Rooms](Rooms.md) |
| Modules | The courses activities belong to | [Modules](Modules.md) |
| Templates | Rules that generate activities | [Templates](Templates.md) |
| Activities | The sessions to schedule | [Activities](Activities.md) |
| Activity groups (`ActivityGroups`) | Which groups attend which activity | [ActivityGroups](ActivityGroups.md) |
| Activity teachers (`ActivityTeachers`) | Which teachers teach which activity | [ActivityTeachers](ActivityTeachers.md) |
| Availability | When a resource cannot or should not be used | [Availability](Availability.md) |
| Constraints | Your rules | [Constraints](Constraints.md) |
| Pins | Activities you fixed in time or place | [Pins](Pins.md) |
| Assignments | A run's result (export only) | [Assignments](Assignments.md) |

The name in brackets is the sheet name in an Excel or CSV file. In the app the tabs show the friendlier name.

## A sensible order to fill them in

1. **Days, Periods, Start patterns**: the shape of the week.
2. **Universities, Levels, Programmes, Groups**, **Teachers**, **Campuses, Buildings, Rooms**: the people and places.
3. **Modules**.
4. **Activities**, with their **ActivityGroups** and **ActivityTeachers**, or **Templates** and then Expand.
5. **Availability**, **Constraints**, **Pins** when you need them.

## Two kinds of columns you will meet

- **Shortcut columns.** `groups` and `teachers` on Activities are conveniences for typing a file by hand. They turn into rows of ActivityGroups and ActivityTeachers when imported, and are never written on export.
- **Filled-in columns.** A few columns, such as `module` and `end` in Assignments, are worked out by the program when you export. You cannot type them.

## Related

- [Tags](tags.md)
- [Constraints and selectors](../constraints/README.md)
- [Glossary](../glossary.md)
