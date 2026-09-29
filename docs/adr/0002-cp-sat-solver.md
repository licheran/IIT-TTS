# ADR-0002: OR-Tools CP-SAT as the solver

- **Status:** Accepted
- **Date:** 2026-09-29

## Context
We need conflict-free assignment with room choice, soft-constraint optimisation, cancellation, progress reporting and infeasibility explanations (FR-8, FR-9, NFR-1, NFR-2).

## Options
1. **A custom heuristic** (greedy with backtracking, or simulated annealing, like FET). Full control, but a lot of work to make reliable, and it can't prove infeasibility.
2. **A MIP solver** (HiGHS, CBC). Good for linear models, but time-indexed scheduling gets large and weak.
3. **CP-SAT.** Native interval and no-overlap constraints, optional intervals for room choice, multi-core search, assumptions for unsat cores, free (Apache 2.0).

## Decision
Use CP-SAT, wrapped behind `solver/` so the core never depends on it.

## Consequences
- The verifier stays independent of the solver.
- Scale strategies (staging, decomposition) live in `solver/` (spec 05 §7).
