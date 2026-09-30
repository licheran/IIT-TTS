# ADR-0007: Sessions the solver creates from demands

- **Status:** Proposed
- **Date:** 2026-09-30

## Context
Today every event is declared before solving. The user either types each activity (Activities with ActivityGroups and ActivityTeachers) or writes Templates whose modes (`joint`, `per_group`, `batched`) decide in advance how many activities there are and which groups share each one (spec 05 §2, FR-5). The solver only chooses times, rooms and pooled resources.

The user wants the timetable built from configuration instead (2026-09-30):
1. A teacher teaches one or more modules, and a module is taught by one or more teachers. The **solver picks the teacher** of each session from the module's teachers.
2. A module lists its session kinds (Lecture, Tutorial, …). A kind's settings (length, online or physical, room type, the maximum number of groups per session, sessions per week) are **configured by the user** once, in a Session types table, and may be overridden per module.
3. A programme (course) at a level has mandatory and optional modules.
4. Each group takes all of its programme's mandatory modules and the optional modules it chooses.
5. **The solver decides which groups share a session**, within the configured maximum number of groups. The room chosen must seat every student of those groups.
6. The solver's output is the Activities table: one row per session (module, kind, groups, teacher, room, day, time). The user may edit it. **Edited fields are kept by the next run; everything not edited is worked out again.**
7. Templates and ActivityGroups go.

Points 1 and 2 need no core change: a pooled requirement already lets the solver choose resources (rooms today, invigilators in the exams preset). Point 5 does. The number of events and each event's fixed resources are no longer known before solving, and the core has no way to say so. Spec 01 §6 lists "individual student enrolment or sectioning" as a non-goal; this ADR keeps individual students out of scope and brings **group-level** splitting in.

Affects FR-5 (replaced), FR-8, FR-10, FR-12, FR-13, FR-14, NFR-1, NFR-2 and NFR-5.

## Options
1. **A new core concept, the demand, that the solver splits into events.**
   A demand says: these participants (exclusive resources) each attend `repeat` events of this kind; each event has at most `max_participants` of them; every event has this duration, start pattern, delivery and these pooled requirements. The solver decides how many events to create, which participants attend each, and when and where each takes place.
   *Pros:* does what the user asked. Generic: nothing academic in the core (a demand could equally split cohorts into exam sittings). It reuses the pooled machinery for rooms and teachers, and the "occupies only if" literals the solver already uses for pooled resources.
   *Cons:* the biggest solver change since Phase 4. Every catalogue compiler must accept events that may not exist and occupancy that depends on membership. The verifier needs a new implicit rule. Runs get slower. Result storage must hold events that are not declared.
2. **Keep grouping deterministic in the preset** (sort the groups and cut them into batches of `max_groups`, like today's `batched` mode, but from configuration).
   *Pros:* no core or solver change; fast; predictable.
   *Cons:* the user explicitly asked for the solver to decide. A fixed cut can make a timetable impossible (two groups whose optional modules clash end up forced into the same session) where a different split would work.
3. **Generate every possible grouping as optional events and let the solver pick a subset** (set partitioning).
   *Pros:* the solver change is only "events may be absent".
   *Cons:* the number of possible groupings grows exponentially (30 groups with up to 3 per session is thousands of candidates per module and kind). It doesn't scale.

## Decision
Option 1, with these rules:

**Core model** (spec 02):
- New concept **Demand**: `code`, `reference?`, `kind`, `participants` (resource codes, exclusive), `max_participants?` (blank means no limit), `repeat ≥ 1`, `duration`, `start_pattern`, `delivery`, `pooled` (pooled specs, as on a template), `tags`.
- `Event` gains `demand?`. An event with a demand counts towards that demand.
- A **created event** is one the solver made for a demand. It is a result, not declared data: it lives in the run (rule 3 still holds), with its participants.

**New implicit hard rule H6 `demand_cover`** (spec 04 §1): for each demand, each participant attends exactly `repeat` of the demand's events (declared or created). Each event has at most `max_participants` participants. The existing rules apply unchanged to created events:
- H1: an event occupies its participants and their exclusive descendants;
- H3: `sum_of_fixed` counts the event's participants.

**Solver** (spec 05 §4):
- For each demand, up to `n = |participants| × repeat` optional events. Each has a presence literal and a membership literal `x[p, e]` per participant:
  - `Σ_e x[p, e] = repeat`;
  - `Σ_p x[p, e] ≤ max_participants · present[e]`;
  - `x[p, e] ⇒ present[e]`.
- A participant's occupancy is an optional interval present iff `x[p, e]`. A pooled choice is present iff `present[e]`.
- Symmetry breaking: presence is ordered, and the lowest participant of each event is ordered.
- A greedy split (participants sorted by code, cut at `max_participants`) is given as a hint.
- `CompileContext.occupying_events` returns membership literals, so the resource-scoped catalogue types (C1–C3, C10, C13, C14) work through the interface they already use. The event-scoped types (C4–C9, C11, C12) are adapted to events that may be absent, one by one, each with its three tests (spec 04 §4).

**New catalogue type C15 `fewest_events`** (soft by default): its penalty is the number of events a demand creates beyond the minimum `⌈|participants| / max_participants⌉ × repeat`. Without it the solver has no reason to prefer fewer sessions. It is a catalogue entry because of rule 7, not a special case.

**Locks come from edited rows, not a new core concept.**
- Editing a solver-made row of Activities saves it as a declared event:
  - its `demand` is set;
  - its groups become fixed participants: any edit fixes the row's groups, since they identify it;
  - an edited teacher becomes a fixed resource;
  - an edited day, start or room becomes a pin.
- Fields not edited stay free: an unedited teacher or room stays a pooled requirement, and an unedited time stays open.
- H6 counts the declared event, so the solver only covers the remaining participants.
- Deleting such a row removes the lock.
- A row typed from scratch, with no demand, is a hand-made event exactly as today. This is how L6 and version 1 workbooks keep working.

**Academic workbook format version 2** (spec 03; exams stays at version 1):
- New sheet **SessionTypes**.
- New columns:
  - `Modules.sessions`: session kinds with optional per-module overrides;
  - `Teachers.modules`: a module, or `module:KIND`;
  - `Programmes.mandatory` and `Programmes.optional`;
  - `Groups.options`.
- **Activities becomes the timetable:** solver rows plus edited and hand-made rows, with a `locked` column naming the kept fields.
- Removed: Templates, ActivityGroups, ActivityTeachers, Pins and the export-only Assignments.
- Version 1 files still import: activities become locked hand-made rows, pins become locked fields, and a version 1 Templates sheet is expanded once on import.
- The preset turns the configuration into demands:
  - one per module and session kind;
  - participants are the groups taking the module;
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
- **Retired:** FR-5 (templates) is replaced by a new requirement for configured sessions. The Templates tab and expander leave the academic UI. `expand/` stays only as the version 1 converter.
- **Phases:** 18 (spec updates), 19 (core and verifier), 20 (solver), 21 (academic configuration, format version 2), 22 (Activities as the editable timetable), 23 (retire Templates and ActivityGroups; wiki), 24 (teacher fairness, last).
- **Decisions to review:**
  - the core name "demand";
  - whether a group must keep the same companions in every repetition (proposed: no);
  - whether subgroups inherit their parent group's modules (proposed: yes; only groups whose parent is a programme are participants);
  - how Excel edits mark locked fields (the `locked` column);
  - the default weight of `fewest_events`.
