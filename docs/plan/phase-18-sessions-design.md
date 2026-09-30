# Phase 18 — Configured sessions: specs and approval

**Goal:** the specs describe timetables built from configuration, where the solver decides which groups share a session, and the user has approved the change before any code moves.

## Read first
- `docs/adr/0007-solver-decided-sessions.md`
- `docs/spec/01-product.md` §4 and §6, `docs/spec/02-domain-model.md` §1–§3 and §6.1, `docs/spec/03-workbook-format.md` §2, `docs/spec/04-constraints.md` §1–§2, `docs/spec/05-solver.md` §2–§5

## Tasks
- [x] P18.1 **Stop and ask:** the user reviews ADR-0007. Record the answers in `docs/STATUS.md` and set the ADR to Accepted (or revise it). No other task starts before this. *(Accepted 2026-09-30. Three proposals are still waiting for the user's confirmation, listed under "Decisions to review" in the ADR. They don't block P18.2–P18.6, but they are written into the specs as proposals.)*
- [x] P18.2 Spec 01:
  - replace FR-5 (templates) with FR-17: "Build sessions from configuration: modules at one level, each mandatory or optional, with session kinds; groups (under a programme) with their optional modules; and teachers with the modules they teach";
  - add FR-18: "The solver decides which groups share a session, in blocks of the configured number of groups, and which of a module's teachers takes it";
  - add FR-19: "The result is the Activities table. A manual edit makes the next run a complete rebuild that keeps the edited values";
  - add FR-20: "Teacher workload fairness", Phase 24;
  - FR-2: the workbook is configuration only, with no timetable and no edits;
  - in §6, keep individual student sectioning as a non-goal and say that group-level splitting is in scope.
- [x] P18.3 Spec 02:
  - add Demand, blocks and `Event.demand` to §1, and say a created event is a run result;
  - add the invariants: participants exclusive; `max_participants ≥ 1`; `repeat ≥ 1`; a dataset is configured (it has demands) or hand-made, not both;
  - in the §3 occupancy rule, say a created event occupies its participants and their exclusive descendants;
  - add the §6.1 academic mapping: Session types, `Modules.level`/`programmes`/`optional`/`sessions`, `Teachers.modules` and `Groups.options` → demands; edits → declared events and pins; a group's parent is a programme (version 2).
- [x] P18.4 Spec 03, format version 2 (academic). A full sheet table for version 2:
  - SessionTypes and the new columns;
  - `Groups.parent` only a programme;
  - the removed sheets (Templates, Activities, ActivityGroups, ActivityTeachers, Pins, Assignments): the version 2 workbook is configuration only;
  - validation messages for every new column.

  Keep the version 1 table as its own section: version 1 still imports into, and exports from, a hand-made dataset. Add a note to `docs/STATUS.md`, as rule 4 requires.
- [ ] P18.5 Spec 04:
  - H6 `demand_cover`, with its semantics: blocks, `repeat` events per block with the same participants, and even block sizes;
  - how each of C1–C14 treats created events: resource-scoped types through membership; event-scoped types and `code:` scopes.
- [ ] P18.6 Spec 05:
  - the pipeline for configured datasets, with no expand step (§1);
  - the new §2, "Demands": block count, even split, edits as declared events;
  - pre-flight checks for demands:
    - no teacher for a module and kind;
    - a block of groups larger than every room of the type;
    - a participant's demand over its free periods;
    - a module with sessions but no groups;
    - an option not offered by the group's programme;
    - a `code:` scope that can't name created events;
    - an edit whose groups no longer match the configuration;
  - the §4 variables and constraints for demands, with symmetry breaking and the greedy hint;
  - explanation rule sets of kind `demand`;
  - result storage.

  Spec 06: the API and table changes.

## Acceptance
- ADR-0007 is Accepted, and the user's answers are in `docs/STATUS.md`.
- Specs 01–06 agree with each other and with the ADR. Every version 2 sheet and column has validation rules, and every new rule has semantics.
