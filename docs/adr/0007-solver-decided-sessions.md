# ADR-0007: Sessions the solver creates from demands

- **Status:** Accepted (design approved by the user on 2026-09-30; the items under "Decisions to review" are proposals the user has not yet confirmed)
- **Date:** 2026-09-30

## Context
Today every event is declared before solving. The user either types each activity (Activities with ActivityGroups and ActivityTeachers) or writes Templates whose modes (`joint`, `per_group`, `batched`) decide in advance how many activities there are and which groups share each one (spec 05 §2, FR-5). The solver only chooses times, rooms and pooled resources.

The user wants the timetable built from configuration instead (2026-09-30):
1. A teacher teaches one or more modules, and a module is taught by one or more teachers. The **solver picks the teacher** of each session from the module's teachers.
2. A module lists its session kinds (Lecture, Tutorial, …). A kind's settings (length, online or physical, room type, the number of groups per session, sessions per week) are **configured by the user** once, in a Session types table, and may be overridden per module.
3. A degree (programme) has levels, and a level has modules. Each module belongs to **exactly one level** and is **mandatory or optional**: a field on the module itself, not a list elsewhere. In the current hierarchy a Programmes row is already one degree at one level (`L6 CS` under `L6`).
4. A group is a set of students who share the **same optional modules**, so a group never has to be split for its options. A group's parent is **always a programme**, never another group (there are no subgroups). Each group takes every mandatory module of its level and degree, plus the optional modules listed in its own `options` field.
5. **The user sets the number of groups in a session** (`n`). **The solver decides which groups share a session.** The room chosen must seat every student of those groups. A group keeps the **same companions** every time its session repeats in the week.
6. The solver's output is the Activities table: one row per session (module, kind, groups, teacher, room, day, time). The user may edit it. **Any manual edit makes the next run a complete rebuild that honours the edit**: the edited values are kept, and everything else is worked out again. The solver never repairs a timetable in place.
7. Templates, ActivityGroups, ActivityTeachers and Pins go from the academic preset's new format: who attends comes from points 3–5, who teaches from point 1, and edits replace pins. The **timetable and the edits are not part of the workbook**: the workbook holds configuration only.

Points 1 and 2 need no core change: a pooled requirement already lets the solver choose resources (rooms today, invigilators in the exams preset). Point 5 does. The events' fixed resources are no longer known before solving, and the core has no way to say so. Spec 01 §6 lists "individual student enrolment or sectioning" as a non-goal; this ADR keeps individual students out of scope and brings **group-level** splitting in.

Affects FR-5 (replaced), FR-8, FR-10, FR-12, FR-13, FR-14, NFR-1, NFR-2 and NFR-5.

## Options
1. **A new core concept, the demand, that the solver splits into blocks.**
   A demand says: these participants (exclusive resources) are divided into blocks of at most `max_participants`; every block attends `repeat` events of this kind; every event has this duration, start pattern, delivery and these pooled requirements. The solver decides who is in which block, and when and where each event takes place.
   *Pros:* does what the user asked. Generic: nothing academic in the core (a demand could equally split cohorts into exam sittings). It reuses the pooled machinery for rooms and teachers. Because the number of blocks is fixed by the configuration, every event always exists (no optional events).
   *Cons:* the biggest solver change since Phase 4. Occupancy of a participant depends on membership. The verifier needs a new implicit rule. Result storage must hold events that are not declared.
2. **Keep grouping deterministic in the preset** (sort the groups and cut them into batches of `n`, like today's `batched` mode, but from configuration).
   *Pros:* no core or solver change; fast; predictable.
   *Cons:* the user explicitly asked for the solver to decide. A fixed cut can make a timetable impossible where a different split would work.
3. **Generate every possible grouping as optional events and let the solver pick a subset** (set partitioning).
   *Cons:* the number of possible groupings grows exponentially. It doesn't scale.

## Decision
Option 1, with these rules:

**Core model** (spec 02):
- New concept **Demand**: `code`, `reference?`, `kind`, `participants` (resource codes, exclusive), `max_participants?` (blank means one block holding everyone), `repeat ≥ 1`, `duration`, `start_pattern`, `delivery`, `pooled` (pooled specs, as on a template), `tags`.
- The number of **blocks** is fixed: `k = ⌈|participants| / max_participants⌉` (1 when there is no limit). The solver splits the participants into `k` blocks whose sizes differ by at most one (for example 10 groups with `n = 3` give 3 + 3 + 2 + 2, never 3 + 3 + 3 + 1). Every block attends `repeat` events, all with the same participants.
- `Event` gains `demand?`. An event with a demand counts towards that demand.
- A **created event** is one the solver made for a demand. It is a result, not declared data: it lives in the run (rule 3 still holds), with its participants.

**New implicit hard rule H6 `demand_cover`** (spec 04 §1): for each demand, the events of the demand (declared or created) form blocks, meaning events with the same participants. Each participant is in exactly one block. Each block has exactly `repeat` events and at most `max_participants` participants, and the block sizes differ by at most one. The existing rules apply unchanged to created events:
- H1: an event occupies its participants and their exclusive descendants;
- H3: `sum_of_fixed` counts the event's participants.

**Solver** (spec 05 §4):
- For each demand, `k` blocks and a membership literal `x[p, b]` per participant and block, with `Σ_b x[p, b] = 1` and `⌊m/k⌋ ≤ Σ_p x[p, b] ≤ ⌈m/k⌉` (`m = |participants|`).
- Each block has `repeat` always-present events with their own start, interval and pooled choices. A participant's occupancy of event `e` of block `b` is an optional interval present iff `x[p, b]`.
- Symmetry breaking: blocks are ordered by their lowest participant.
- A greedy split (participants sorted by code, cut into `k` even blocks) is given as a hint.
- `CompileContext.occupying_events` returns membership literals, so the resource-scoped catalogue types (C1–C3, C10, C13, C14) work through the interface they already use. The event-scoped types (C4–C9, C11, C12) are adapted one by one, each with its three tests (spec 04 §4).
- There is no "fewest sessions" rule: the number of sessions is fixed by `n`.

**Edits are inputs to a complete rebuild, not a new core concept.**
- Editing a solver-made row of Activities saves a declared event:
  - its `demand` is set;
  - its groups become that block's fixed participants (any edit keeps the row's groups together, since they identify the row);
  - an edited teacher becomes a fixed resource;
  - an edited day, start or room becomes a pin.
- Fields not edited stay free.
- H6 counts the declared events. A block with fewer declared events than `repeat` gets the missing repetitions created by the solver, with the same groups. The remaining participants fill the remaining blocks.
- Edits are stored against the demand and the block's groups, so they keep working across runs. An edit whose groups no longer match the configuration is reported by pre-flight and ignored.
- An edit does not start a run by itself: the timetable shows "N edits waiting" and a **Rebuild** button (the Start button). The rebuild is always complete: nothing is patched in place.
- **Undo edit** on a session, and **Clear all edits**, remove them.
- A dataset is either **configured** (it has demands) or **hand-made** (events typed or imported from a version 1 workbook, as today: L6 is one). They are not mixed. A configured dataset has no "add row" on Activities.

**Academic workbook format version 2** (spec 03; exams stays at version 1):
- New sheet **SessionTypes**.
- New and changed columns:
  - `Modules.level`: exactly one level, now required (today it is information only);
  - `Modules.programmes`: the degrees at that level that take the module, a list; blank means every programme at the level;
  - `Modules.optional`: true or false (default false, meaning mandatory);
  - `Modules.sessions`: session kinds with optional per-module overrides;
  - `Teachers.modules`: a module, or `module:KIND`;
  - `Groups.options`: the group's optional modules. Each must be an optional module of the group's level and programme;
  - `Groups.parent` must be a programme.
  - Programmes, Levels and Universities keep their columns: no module lists there.
- The workbook holds **configuration only**. It has no Activities, Assignments or edits. Timetable results are exported from the Timetable tab (HTML, Excel and CSV), which are outputs, not workbooks to import.
- Removed: Templates, ActivityGroups, ActivityTeachers, Pins and the export-only Assignments sheet.
- Version 1 files still import, into a hand-made dataset: activities, groups, teachers and pins become events, fixed resources and pins; a Templates sheet with rows is expanded once on import. A hand-made dataset exports as version 1 (the only format that can hold its events). A configured dataset exports as version 2.
- The preset turns the configuration into demands:
  - one per module and session kind;
  - participants are the groups taking the module: for a mandatory module, every group of its programmes at its level; for an optional module, only those groups that list it in `options`;
  - pooled Room: `tag:room_type=<t>` and `sum_of_fixed:StudentGroup`;
  - pooled Teacher: filter `code:<the module's teachers for that kind>`.

  All academic words stay in the preset.

## Consequences
- **Easier:** configuring a term. There is nothing to type per session, and there are no templates. The solver can find splits a fixed rule would miss.
- **Harder:** solve time. Membership literals multiply the model. P20 measures an L6-sized configuration against a target (≤ 120 s feasible on 4 cores). NFR-1 still applies to L6 as a hand-made dataset. If the target is missed, stop and ask before loosening anything.
- **The verifier** gains H6 and checks created events from the stored result. It still never imports the solver.
- **Result storage:** `assignment` rows may belong to a created event (with its kind, demand and participants) and not to a declared event. This needs a migration.
- **Decomposition** (Phase 10) and **explanation** (spec 05 §5) learn about demands. Explanations get a rule set of kind `demand` per participant.
- **Event-scoped constraints** whose scope uses `code:` cannot name created events, because codes don't exist before solving. Pre-flight warns. Scopes should use `ref:`, `kind:` and `uses:`. `uses:` on a created event is a membership literal.
- **Retired:** FR-5 (templates) is replaced by a new requirement for configured sessions. The Templates tab and expander leave the academic UI, and so do the ActivityGroups, ActivityTeachers and Pins tables (hand-made datasets show groups and teachers as columns of Activities). `expand/` stays only as the version 1 converter.
- **Edits do not travel in a workbook.** Exporting a configured dataset and importing it elsewhere brings the configuration, not the edits. A later format version could add a small sheet for them.
- **One flag per module:** because mandatory/optional is a field of the module, one module cannot be mandatory for one degree and optional for another at the same level. That needs two module rows (two codes).
- **No subgroups in version 2.** A version 1 dataset with a group under a group stays valid as a hand-made dataset. A version 2 workbook with one is refused.
- **Phases:** 18 (spec updates), 19 (core and verifier), 20 (solver), 21 (academic configuration, format version 2), 22 (editing sessions: edits and complete rebuild), 23 (retire Templates and ActivityGroups; wiki), 24 (the Session table, see the amendment below), 25 (teacher fairness, last).
- **Decisions to review** (proposals the user has not yet confirmed):
  - the even split (sizes differ by at most one) rather than "as full as possible" (3 + 3 + 3 + 1);
  - the one-flag-per-module limit above;
  - that an edit waits for **Rebuild** instead of starting a run by itself.

## Amendment 1 (2026-09-30): a Session table instead of `Modules.sessions`

Decided by the user after Phase 23; built in Phase 24 (`docs/plan/phase-24-session-table.md`), where the specs are updated.

- A module's sessions move from the inline list `Modules.sessions` (`LEC;TUT;LAB(start_pattern=3H,max_groups=2)`) to a new sheet **`Session`**: one row per module and session type, with the columns `module`, `session_type`, `start_pattern`, `delivery`, `room_type`, `max_groups`, `teachers`, `weekly` and `tags`. A blank cell takes the session type's value; a filled cell overrides it for that module only. So a module's lecture can have several groups per session and its tutorial one, each set per module.
- `Teachers.modules` is unchanged (`module` or `module:KIND`).
- Workbook format version 2 is **amended, not bumped**: no version 2 file exists outside the repository, and the `l6-config.xlsx` fixture is regenerated. A version 2 file with a `Modules.sessions` column is refused.
- The demands, and the session and edit codes, are unchanged (`<module>-<session_type>`), so the solver, the verifier and Phase 22's edits need no change.
- **Why:** the inline list is a small language inside one cell: no dropdowns, errors that point at a whole string, and no sorting or filtering. A table gives each setting its own checked cell.

