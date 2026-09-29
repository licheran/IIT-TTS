# Phase 4 — Solver v1 (hard constraints)

**Goal:** conflict-free time and room allocation, fully verified. This retires the main technical risk.

## Read first
- `docs/spec/05-solver.md` §1, §4.1, §4.2, §4.4
- `docs/spec/04-constraints.md` §1

## Tasks
- [ ] P4.1 `solver/context.py`: `CompileContext` holding the model, the variable maps (`start`, `iv`, `day_is`, `use`, `oiv`), and the helpers `occupants(resource)` and `penalty(name)`.
- [ ] P4.2 `solver/compile.py`:
  - Start domains (allowed starts minus fixed-resource unavailability, intersected with pins).
  - Candidate pre-filtering for pooled requirements (H3, H4).
  - `AddNoOverlap` per exclusive resource, with hierarchy propagation.
  - Pooled unavailability, and locks.
- [ ] P4.3 `solver/solve.py`: apply `RunParams` (spec 05 §4.4). Return `SolveOutcome(status, result|None, stats)`.
- [ ] P4.4 `solver/decode.py`: build the `Result` from the solution.
- [ ] P4.5 `cli.py solve`: workbook in, result workbook out (with the `Assignments` sheet), print the stats and verifier summary. Exit code 0 when feasible, 2 when infeasible, 3 when invalid.
- [ ] P4.6 Tests, all asserting through the verifier:
  - Every Phase 1 mini case, solved.
  - Property test: random feasible datasets (generated from a random valid assignment) always solve with 0 violations.
- [ ] P4.7 L6 tests:
  - (a) With the locks as pins, the solver reproduces the original exactly.
  - (b) With no pins, it is feasible, all 77 placed, 0 violations, in ≤ 30 s (NFR-1).
  - (c) Determinism with `num_workers=1` and a fixed seed (NFR-3).

## Acceptance
- `uv run tts solve tests/fixtures/l6/l6.xlsx --out /tmp/l6-out.xlsx --time-limit 30` exits 0, and the verifier summary shows 0 hard violations.
- Every P4.6 and P4.7 test passes.

## Out of scope
Soft constraints, explanations (Phase 5) and the database.
