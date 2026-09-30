# Glossary

Terms are listed alphabetically. The academic words (group, teacher, room) are the ones the academic preset shows in the app.

| Term | Meaning |
|---|---|
| **Activity** | One session in the timetable, for example one lecture of one module for one or more groups. In a dataset built from configuration the Activities are made by the solver (see *Session*); in a hand-made dataset they are typed or imported. The program calls it an *event* in some technical places. |
| **Assignment** | The result for one activity in a run: the day, the start period and the rooms chosen. |
| **Availability** | A statement that a resource (a teacher, a room, a group) cannot be used, or had better not be used, in a day and period. |
| **Block** | The groups that meet together in one session. The solver splits a module's groups into blocks of at most the session type's `max_groups` (as even as it can), and a block keeps the same companions for every session of the week. |
| **Break** | A period marked `is_break`. No activity may cover a break. |
| **Clash** | A group, teacher or room is needed by two activities in the same period. The timetable never contains one. |
| **Code** | The unique name of a row inside the data. See [Basics](basics.md). |
| **Configured dataset** | A dataset whose workbook holds configuration only (format version 2): the solver makes the sessions. |
| **Constraint** | A rule. A **hard** constraint must hold. A **soft** constraint is a preference that adds to the score when broken. |
| **Dataset** | Everything for one timetable: the tables you entered, plus the runs made from them. |
| **Delivery** | How an activity is given. `in_person` needs a room. `online` needs none. |
| **Duration** | How many consecutive periods an activity lasts. |
| **Edit** | A value you keep in a session of a configured dataset (its day, start, rooms, teachers or groups). The next run is a complete rebuild that keeps every edit. |
| **Feasible** | Every activity is placed, and every hard constraint holds. |
| **Fixed requirement** | Something an activity always needs, such as the groups attending or the teacher. Fixed means you named it. |
| **Hand-made dataset** | A dataset whose activities are typed or imported (format version 1, such as L6). The solver only places them. |
| **Joint activity** | An activity that several groups attend together. It occupies all of them. |
| **Lock** | A pin created from another dataset's published timetable, so that two datasets that share teachers or rooms do not clash. |
| **Period** | One time slot in a day, with a start and an end. |
| **Pin** | A time, and optionally rooms, that you fix for an activity of a hand-made dataset. The solver then keeps it. In a configured dataset you *edit* the session instead. |
| **Pooled requirement** | Something an activity needs that the solver chooses, such as a room of a given type with enough seats. Pooled means you named the kind, and the solver picks the one. |
| **Pre-flight** | The checks made before solving. Errors stop a run from starting. |
| **Preset** | A packaged set of tables, labels and default rules for one kind of timetable. |
| **Publish** | Mark one run of a dataset as the official one. There is at most one published run per dataset. |
| **Rebuild** | A run that solves everything again from scratch and keeps the edits you made. |
| **Resource** | Anything that can be used by one activity at a time, or that groups others: a group, a teacher, a room, and also a programme, a building and so on. |
| **Run** | One attempt to solve a dataset, with its settings, progress and result. Every run keeps a frozen copy of its data. |
| **Score** | The sum of `weight × penalty` over all soft constraints. Lower is better. `0` means every preference is met. |
| **Selector** | A short text such as `under:L6 SE` that picks rows, used in rule scopes and templates. |
| **Session** | One meeting the solver makes from a module and a session type, for example one tutorial for one block of groups. |
| **Session type** | A kind of session (`LEC`, `TUT`, your own) with its length, delivery, room type, groups per session and sessions per week. Modules list the session types they have. |
| **Start pattern** | The list of periods an activity of a given length may start in. |
| **Tag** | A `key=value` label on a resource or an activity, used by selectors. |
| **Template** | Retired. A rule that generated activities. A version 1 file's template rows are expanded once when it is imported. |
