# Phase 27 — Scale target for configured datasets

**Goal:** close the open point of P20.8. A configured dataset of institute size (about 2,700 sessions from 384 demands, 180 of them with free splits) finds a timetable within NFR-2 (15 minutes on 8 workers). Today it finds none in 900 s. The same institute written as hand-made activities solves in about 58 s, so the difficulty comes from the choices the solver was given (who shares a session, which teacher), not from size.

**Decided by the user (2026-10-09):** this is a last investigation task. The 15-minute assertion is **never loosened**. If the target is still missed, the result is an honest report with numbers and the options left, and the `xfail` stays.

## Read first
- `docs/LOG.md`, the rows P20.5–P20.8 (what was tried: the plain model, the decomposed model, the default split first)
- `docs/spec/05-solver.md` §2.2, §4.1a, §7 (demands, membership literals, decomposition)
- `backend/src/tts/solver/{compile,decompose,solve}.py`, `backend/src/tts/core/demands.py`
- `backend/tests/scale/test_solve_scale_demands.py`, `backend/tests/scale/generate.py`

## Tasks
- [ ] P27.1 Measure the baseline on the current code (`uv run pytest -m scale tests/scale/test_solve_scale_demands.py`, 8 workers): time, status, and the CP-SAT log for the first 5 minutes (number of variables and constraints, first-solution time). Record the numbers in `docs/LOG.md`. No code change.
- [ ] P27.2 Option (a): the default split (participants in code order, cut into even blocks) is the first attempt and gets most of the time budget; the free search only gets what is left. Measure with 3 seeds. Keep it only if it finds a timetable and the verifier reports 0 hard violations. If the default split is used, the result still carries the warning "participants were split by the default split … the solver did not search other splits".
- [ ] P27.3 Only if P27.2 misses: option (c), a staged model. Stage 1 fixes times and block membership with room capacity and teacher load relaxed to aggregates; stage 2 chooses rooms and teachers for the sessions made. Reuse `solve_dataset`'s existing times-first decomposition (P20.7) before writing anything new. A new constraint behaviour still needs a catalogue entry (CLAUDE.md rule 7).
- [ ] P27.4 Report. If a timetable is found within 15 minutes with 0 hard violations: remove the `xfail` from the scale test and tick P20.8 in `phase-20-demands-solver.md`. If not: keep the `xfail`, update its reason with the new numbers, and write the remaining options in `docs/STATUS.md` ("Decisions waiting") for the user: (b) let the user fix teachers per module for large sites, (d) change the target.

## Acceptance
- The scale test passes its unchanged 15-minute assertion, **or** the log shows the measured numbers of every option tried and the `xfail` reason is updated with them.
- L6 (`expected.json`), the configured L6 fixture and the fast test suite are unchanged and green.
- No test or acceptance criterion was loosened.
