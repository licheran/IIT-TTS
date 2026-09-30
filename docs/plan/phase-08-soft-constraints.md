# Phase 8 — Soft constraints and scoring

**Goal:** good timetables, not just valid ones.

## Read first
- `docs/spec/04-constraints.md` §0, §2, §3, §4
- `docs/spec/05-solver.md` §4.3

## Tasks
- [x] P8.1 Implement C1–C14. Each type needs a `core/constraints/<type>.py` verify, a `solver/constraints/<type>.py` compile, and the three tests required by spec 04 §4. Do one type per commit.
- [x] P8.2 Objective and score breakdown stored on the run (`score_breakdown` keyed by constraint code).
- [x] P8.3 Academic defaults (spec 04 §3) in `presets/academic_weekly/defaults.py`. They are applied to new datasets and to `import-fet` output.
- [x] P8.4 `mode=two_phase` in `RunParams` (spec 05 §4.4).
- [x] P8.5 Catalogue completeness test (spec 06 §8, gate 4).
- [x] P8.6 Remove the xfail from the Phase 5 `max_days` broken variant.

## Acceptance
- With the defaults enabled, the L6 penalty is lower than the penalty of the hard-only solution (verifier-computed) under the same time limit, and there are 0 hard violations.
- All catalogue tests pass.
