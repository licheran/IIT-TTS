# Phase 25 — Teacher fairness

**Goal:** when the solver chooses teachers, the workload is shared sensibly: no one is given more than their weekly hours, sessions are spread across a module's teachers, and a group keeps the same teacher.

## Read first
- Phase 24 (the Session table) comes first: `Teachers.max_hours` below is another amendment of format version 2, made the same way.
- `docs/spec/04-constraints.md` §2–§4, and ADR-0005 (fixed catalogue)
- `backend/src/tts/core/constraints/`, `backend/src/tts/solver/constraints/`

## Tasks
- [ ] P25.1 **Stop and ask:** confirm the three rules below, their default hard/soft settings and weights, and whether "share of the load" means equal shares or shares set per teacher. Update spec 04 and the ADR log with the answers.
- [ ] P25.2 C15 `max_load` (resources):
  - params `max:int`, `unit: "events"|"periods"`;
  - the occupied periods (or sessions) of each resource over the week are at most `max`;
  - penalty: the excess.

  The academic column `Teachers.max_hours` (whole number ≥ 0, blank for no limit) becomes a hard `max_load` per teacher. That column is a format change, so bump or amend version 2 before release and note it in STATUS. Verify, compile and the three tests.
- [ ] P25.3 C16 `balance_load` (resources):
  - within the scope, the difference between the most and the least loaded resource (in periods), or the deviation from each resource's share when shares are given;
  - penalty: that difference.

  The academic default is `FAIR-<module>` over each module's teachers, soft. Verify, compile and the three tests.
- [ ] P25.4 C17 `same_resource` (events):
  - params `type: <ResourceType>`, `per: <ResourceType>`;
  - for each resource of type `per` (a group), its events in scope use the same pooled resource of type `type` (a teacher);
  - penalty: the number of events that don't use the most common one.

  The academic default is `CONT-<module>-<kind>`, soft. Verify, compile and the three tests.
- [ ] P25.5 Check that the existing resource-scoped types hold for chosen teachers: `max_per_day`, `max_gaps`, `max_days`, `max_span` and `avoid`. Add one test each with a teacher chosen by the solver.
- [ ] P25.6 Wiki pages for the three new types (their Parameters tables are checked against `Params`), the defaults page, and the Teachers page (`max_hours`).

## Acceptance
- On `l6-config.xlsx` with `max_hours` set for every teacher, no teacher exceeds it (verifier: 0 hard violations).
- Load balance and continuity improve against a run without them. The score breakdown shows each rule's penalty.
- The catalogue gate lists 17 types, each with verify, compile and three tests.
