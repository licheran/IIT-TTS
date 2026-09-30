# Glossary

Terms are listed alphabetically. The academic words (group, teacher, room) are the ones the academic preset shows in the app.

| Term | Meaning |
|---|---|
| **Activity** | One session to schedule, for example one lecture of one module for one or more groups. The table is called Activities. The program calls it an *event* in some technical places. |
| **Assignment** | The result for one activity in a run: the day, the start period and the rooms chosen. |
| **Availability** | A statement that a resource (a teacher, a room, a group) cannot be used, or had better not be used, in a day and period. |
| **Break** | A period marked `is_break`. No activity may cover a break. |
| **Clash** | A group, teacher or room is needed by two activities in the same period. The timetable never contains one. |
| **Code** | The unique name of a row inside the data. See [Basics](basics.md). |
| **Constraint** | A rule. A **hard** constraint must hold. A **soft** constraint is a preference that adds to the score when broken. |
| **Dataset** | Everything for one timetable: the tables you entered, plus the runs made from them. |
| **Delivery** | How an activity is given. `in_person` needs a room. `online` needs none. |
| **Duration** | How many consecutive periods an activity lasts. |
| **Feasible** | Every activity is placed, and every hard constraint holds. |
| **Fixed requirement** | Something an activity always needs, such as the groups attending or the teacher. Fixed means you named it. |
| **Joint activity** | An activity that several groups attend together. It occupies all of them. |
| **Lock** | A pin created from another dataset's published timetable, so that two datasets that share teachers or rooms do not clash. |
| **Period** | One time slot in a day, with a start and an end. |
| **Pin** | A time, and optionally rooms, that you fix for an activity. The solver then keeps it. |
| **Pooled requirement** | Something an activity needs that the solver chooses, such as a room of a given type with enough seats. Pooled means you named the kind, and the solver picks the one. |
| **Pre-flight** | The checks made before solving. Errors stop a run from starting. |
| **Preset** | A packaged set of tables, labels and default rules for one kind of timetable. |
| **Publish** | Mark one run of a dataset as the official one. There is at most one published run per dataset. |
| **Resource** | Anything that can be used by one activity at a time, or that groups others: a group, a teacher, a room, and also a programme, a building and so on. |
| **Run** | One attempt to solve a dataset, with its settings, progress and result. Every run keeps a frozen copy of its data. |
| **Score** | The sum of `weight × penalty` over all soft constraints. Lower is better. `0` means every preference is met. |
| **Selector** | A short text such as `under:L6 SE` that picks rows, used in rule scopes and templates. |
| **Start pattern** | The list of periods an activity of a given length may start in. |
| **Tag** | A `key=value` label on a resource or an activity, used by selectors. |
| **Template** | A rule that generates activities, for example "every module gets one lecture for all its groups and one tutorial per group". |
