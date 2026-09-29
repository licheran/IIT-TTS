# Phase 5 — Pre-flight checks and infeasibility explanations

**Goal:** failures are fast, specific and readable.

## Read first
- `docs/spec/05-solver.md` §3, §5

## Tasks
- [x] P5.1 `preflight/checks.py`: every check in spec 05 §3, returning `Issue(severity, kind, message, refs)`. Messages use codes and preset labels (labels are passed in, so the core stays neutral).
- [x] P5.2 Integrate pre-flight into `cli.py solve`. Errors block the solve and exit with code 4.
- [x] P5.3 `solver/explain.py`: the assumption-literal re-solve, core extraction and greedy shrinking (spec 05 §5), turned into a `Diagnostic`.
- [x] P5.4 A broken-L6 suite in `tests/integration/test_l6_broken.py`. Each variant has one expected message pattern:
  - The Auditorium is removed (no candidate room).
  - Teacher HAWE is made unavailable Tue–Sat (over-demand). (Tue–Fri leaves Mon and Sat, 26 periods for 16 needed, so it cannot trigger over-demand; changed with the user's approval, 2026-09-29.)
  - Two pins are put on the same room and slot (conflicting pins).
  - A hard `max_days: 1` is set for the `L6 SE / G1` group (infeasible core names that constraint). This case waits until Phase 8 adds `max_days`, so leave its test marked xfail until then.
- [ ] P5.5 A timing test: pre-flight on L6 takes ≤ 1 s (NFR-7).

## Acceptance
- Each broken variant produces the expected issue or diagnostic, with the right entity codes.
- No variant runs longer than 60 s.
