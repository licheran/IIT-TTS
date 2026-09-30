# Phase 20 — The solver splits demands into sessions

**Goal:** the solver creates the sessions of each demand, decides which participants attend each, and places and resources them, and the verifier finds no hard violation in what it returns.

## Read first
- `docs/adr/0007-solver-decided-sessions.md`
- `docs/spec/05-solver.md` §4, §5 and §7, `docs/spec/04-constraints.md` §1 and §2
- `backend/src/tts/solver/context.py`, `solver/compile.py`, `solver/decode.py`, `solver/explain.py`, `solver/decompose.py`, `solver/constraints/`

## Tasks
- [ ] P20.1 Variables for demands:
  - up to `|participants| × repeat` optional events per demand, each with a presence literal, a start over the start pattern's allowed starts, and an optional interval;
  - a membership literal `x[p, e]` per participant, with `Σ_e x[p, e] = repeat`, `Σ_p x[p, e] ≤ max_participants · present[e]` and `x[p, e] ⇒ present[e]`;
  - a participant's occupancy (and its exclusive descendants') is an optional interval present iff `x[p, e]`, added to its no-overlap set;
  - pooled requirements: `Σ_r use[e, q, r] = count · present[e]`;
  - capacity (H3): `use[e, q, r] ⇒ Σ_p size(p) · x[p, e] ≤ capacity(r)`;
  - unavailable slots (H2) for a participant apply under `x[p, e]`.

  Tests assert on the verifier's output, not on solver status.
- [ ] P20.2 Symmetry breaking and the hint:
  - `present[e_k] ≥ present[e_{k+1}]`;
  - each participant may only join events up to its own index;
  - a greedy split (participants by code, cut at `max_participants`) is given with `AddHint`.

  A test that the model with symmetry breaking gives the same optimum as without it on a small case, with a fixed seed and one worker.
- [ ] P20.3 `CompileContext` learns created events:
  - `occupying_events` returns membership literals;
  - `start_is`, `covering`, `day_is` and `day_var` hold only when the event is present;
  - event selectors resolve `uses:` to a membership literal.

  Unit tests of each building block with a present and an absent event.
- [ ] P20.4 Adapt every catalogue compiler in `solver/constraints/` (C1–C14) to created events, one commit per type. Each gets its three tests plus one with a created event. Then add the compiler of C15 `fewest_events` and the academic default `SES-FEWEST` (soft; its weight is the value the user picked in P18.1).
- [ ] P20.5 Decode:
  - created events are numbered `<prefix>-<kind>-<nn>`, where the prefix is the demand's reference or code, in order of their first participant's code, so the same solution always gives the same codes;
  - the result carries their participants.

  The run store keeps created events (a migration: `assignment` rows may point to a created event with its demand, kind and participants). The solver still writes only `assignment` and `assigned_resource` rows (rule 3).
- [ ] P20.6 Explanation: one rule set of kind `demand` per participant and demand. It covers the participant's cover and the demand's `max_participants`. Test: a demand whose groups can't all fit into the periods they have free is explained with the group and the module named.
- [ ] P20.7 Decomposition (spec 05 §7) with demands. Either the times-first half fixes membership and times, and the second half chooses rooms and teachers; or decomposition is switched off for datasets with demands, and the reason is recorded. Measure both on the P20.8 dataset and pick one, recording it in STATUS.
- [ ] P20.8 Measure:
  - a configuration dataset the size of L6 (the L6 modules, groups, teachers and rooms, with session types instead of hand-made activities; assumptions recorded in `_meta`), built in the core for now;
  - target: feasible in ≤ 120 s on 4 cores, and the verifier finds 0 hard violations;
  - a `scale` test: the Phase 10 synthetic institute written as demands; report the time.

  **If a target is missed, stop and ask** before loosening anything.

## Acceptance
- On the L6-sized configuration, the solver creates sessions for every module and kind, every group attends each of its modules' sessions `repeat` times, no session has more than its maximum number of groups, every room seats its session's groups, and every teacher is one of the module's teachers. The verifier reports 0 hard violations, within the P20.8 target.
- L6 as hand-made activities still meets NFR-1 and `expected.json`.
- The catalogue completeness gate lists 15 types with verify and compile, and the three tests each.
