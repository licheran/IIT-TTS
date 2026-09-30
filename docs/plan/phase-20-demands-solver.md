# Phase 20 — The solver splits demands into sessions

**Goal:** the solver divides each demand's groups into blocks, places every block's sessions and gives them rooms and teachers, and the verifier finds no hard violation in what it returns.

## Read first
- `docs/adr/0007-solver-decided-sessions.md`
- `docs/spec/05-solver.md` §4, §5 and §7, `docs/spec/04-constraints.md` §1 and §2
- `backend/src/tts/solver/context.py`, `solver/compile.py`, `solver/decode.py`, `solver/explain.py`, `solver/decompose.py`, `solver/constraints/`

## Tasks
- [x] P20.1 Variables for demands:
  - `k = Demand.blocks` blocks per demand and a membership literal `x[p, b]` per participant and block, with `Σ_b x[p, b] = 1` and `⌊m/k⌋ ≤ Σ_p x[p, b] ≤ ⌈m/k⌉`;
  - each block has `repeat` events, always present, each with a start over the start pattern's allowed starts, an interval and its pooled choices (`Σ_r use[e, q, r] = count`);
  - a participant's occupancy of an event (and its exclusive descendants') is an optional interval present iff `x[p, b]`, added to its no-overlap set;
  - capacity (H3): `use[e, q, r] ⇒ Σ_p size(p) · x[p, b] ≤ capacity(r)`;
  - a participant's unavailable slots (H2) apply under `x[p, b]`;
  - edits: a declared event of a demand fixes its block's participants (those `x[p, b]` are constants), and its pins apply as today. A block with fewer declared events than `repeat` gets the rest created.

  Tests assert on the verifier's output, not on solver status.
- [x] P20.2 Symmetry breaking and the hint:
  - blocks are ordered by their lowest participant: participant `i` may only be in blocks `≤ i`, and block `b` holds the lowest participant not in blocks `< b`;
  - a greedy split (participants by code, cut into `k` even blocks) is given with `AddHint`.

  A test that the model gives the same optimum with and without symmetry breaking on a small case, with a fixed seed and one worker.
- [x] P20.3 `CompileContext` learns created events:
  - `occupying_events` returns membership literals;
  - event selectors resolve `uses:` to a membership literal.

  Unit tests of each building block with a member and a non-member.
- [x] P20.4 Adapt every catalogue compiler in `solver/constraints/` (C1–C14) to created events, one commit per type. Each gets its three tests plus one with a created event.
- [x] P20.5 Decode:
  - created events are numbered `<prefix>-<kind>-<nn>`, where the prefix is the demand's reference or code, in order of their block's lowest participant, then repetition, so the same solution always gives the same codes;
  - the result carries their participants.

  The run store keeps created events (a migration: `assignment` rows may point to a created event with its demand, kind and participants). The solver still writes only `assignment` and `assigned_resource` rows (rule 3).
- [x] P20.6 Explanation: one rule set of kind `demand` per participant and demand. It covers the participant's block membership and the block sizes. Test: a demand whose groups can't all fit into the periods they have free is explained with the group and the module named.
- [x] P20.7 Decomposition (spec 05 §7) with demands. Either the times-first half fixes membership and times, and the second half chooses rooms and teachers; or decomposition is switched off for configured datasets, and the reason is recorded. Measure both on the P20.8 dataset and pick one, recording it in STATUS.
- [ ] P20.8 Measure (L6-sized target met; the synthetic institute target is **missed**, see STATUS):
  - a configured dataset the size of L6 (the L6 modules, groups, teachers and rooms, with session types instead of hand-made activities; assumptions recorded in `_meta`), built in the core for now;
  - target: feasible in ≤ 120 s on 4 cores, and the verifier finds 0 hard violations;
  - a `scale` test: the Phase 10 synthetic institute written as demands; report the time.

  **If a target is missed, stop and ask** before loosening anything.

## Acceptance
- On the L6-sized configured dataset:
  - every group is in exactly one block of each of its modules' session kinds, and blocks have even sizes of at most the configured number of groups;
  - every block has its `repeat` sessions with the same groups;
  - every room seats its session's groups;
  - every teacher is one of the module's teachers.

  The verifier reports 0 hard violations, within the P20.8 target.
- L6 as a hand-made dataset still meets NFR-1 and `expected.json`.
- The catalogue completeness gate still lists all 14 types with verify, compile and the three tests each.
