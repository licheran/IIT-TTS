# Phase 18 — Configured sessions: specs and approval

**Goal:** the specs describe timetables built from configuration, where the solver decides which groups share a session, and the user has approved the change before any code moves.

## Read first
- `docs/adr/0007-solver-decided-sessions.md`
- `docs/spec/01-product.md` §4 and §6, `docs/spec/02-domain-model.md` §1–§3 and §6.1, `docs/spec/03-workbook-format.md` §2, `docs/spec/04-constraints.md` §1–§2, `docs/spec/05-solver.md` §2–§5

## Tasks
- [ ] P18.1 **Stop and ask:** the user reviews ADR-0007, including its "Decisions to review". Record the answers in `docs/STATUS.md` and set the ADR to Accepted (or revise it). No other task starts before this.
- [ ] P18.2 Spec 01:
  - replace FR-5 (templates) with FR-17: "Build sessions from configuration: modules with session kinds, programmes with mandatory and optional modules, groups with their options, and teachers with the modules they teach";
  - add FR-18: "The solver decides which groups share a session (within a configured maximum) and which of a module's teachers takes it";
  - add FR-19: "The result is an editable Activities table; edited fields are kept by the next run";
  - add FR-20: "Teacher workload fairness", Phase 24;
  - in §6, keep individual student sectioning as a non-goal and say that group-level splitting is in scope.
- [ ] P18.3 Spec 02:
  - add Demand and `Event.demand` to §1, and say a created event is a run result;
  - add the invariants (participants exclusive, `max_participants ≥ 1`, `repeat ≥ 1`);
  - in the §3 occupancy rule, say a created event occupies its participants and their exclusive descendants;
  - add the §6.1 academic mapping: Session types, `Modules.sessions`, `Teachers.modules`, `Programmes.mandatory`/`optional` and `Groups.options` → demands; edited rows → declared events and pins.
- [ ] P18.4 Spec 03, format version 2 (academic). A full sheet table for version 2:
  - SessionTypes; the new columns; Activities as the timetable with `locked`;
  - the removed sheets;
  - the version 1 → version 2 conversion rules, and validation messages for every new column.

  Keep the version 1 table as a section for the converter. Add a note to `docs/STATUS.md`, as rule 4 requires.
- [ ] P18.5 Spec 04:
  - H6 `demand_cover`, with its semantics;
  - C15 `fewest_events`, with parameters, semantics and penalty;
  - how each of C1–C14 treats created events: resource-scoped types through membership; event-scoped types and `code:` scopes;
  - the academic default `SES-FEWEST`.
- [ ] P18.6 Spec 05:
  - the pipeline without an expand step for version 2 (§1);
  - the new §2, "Demands";
  - pre-flight checks for demands: no teacher for a module and kind; a group larger than every room of the type; a participant's demand over its free periods; a module with sessions but no groups; an option not offered by the group's programme; a `code:` scope that can't name created events;
  - the §4 variables and constraints for demands, with symmetry breaking and the greedy hint;
  - explanation rule sets of kind `demand`;
  - result storage.

  Spec 06: the API and table changes.

## Acceptance
- ADR-0007 is Accepted, and the user's answers to its open decisions are in `docs/STATUS.md`.
- Specs 01–06 agree with each other and with the ADR. Every version 2 sheet and column has validation rules, and every new rule has semantics and a penalty.
