# Phase 10 — Scale: multiple levels, programmes, universities and buildings

**Goal:** institute-wide, conflict-free timetabling.

## Read first
- `docs/spec/01-product.md` §2.1, §2.3
- `docs/spec/05-solver.md` §7

## Tasks
- [x] P10.1 `tests/scale/generate.py`: a synthetic workbook generator. Parameters:
  - levels (L4–L7), programmes (CS, SE, BDS, AIDS, …), universities (UOW, RGU, …),
  - groups per programme, modules per level,
  - share of teachers shared across programmes,
  - buildings (GP, Java, Rama, Dialog, Spencer, …) with rooms per building and room-type mix.

  The generator builds a feasible hidden assignment first, so feasibility is guaranteed.
- [x] P10.2 Staged solving by scope selector (for example `uses:(under:L4)`), with earlier stages locked. Available in the CLI (`--stage`) and the API (`RunParams.stage_scope`).
- [x] P10.3 A cross-dataset clash report: check every published run that shares resource codes and report the clashes.
- [x] P10.4 Profile, then apply only the measured wins from spec 05 §7 (symmetry breaking, decomposition, hints). Record the before and after numbers in STATUS.
- [x] P10.5 Scale tests (`scale` marker): about 3,000 events, feasible in ≤ 15 min on 8 cores (NFR-2). Staged L4→L7 has no cross-stage clashes.

## Acceptance
- The P10.5 tests pass, or the gap is measured and documented, with an ADR for the next step.
