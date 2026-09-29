# Roadmap

Work through the phases in order. A phase is done when all its tasks are ticked **and** its Acceptance section passes. The current phase is recorded in `../STATUS.md`.

| Phase | File | Outcome | Requirements |
|---|---|---|---|
| 0 | [phase-00-setup.md](phase-00-setup.md) | Repo, tooling, CI, compose skeleton | — |
| 1 | [phase-01-core-and-verifier.md](phase-01-core-and-verifier.md) | Domain-neutral model + independent verifier | FR-4, FR-14 |
| 2 | [phase-02-l6-fixture.md](phase-02-l6-fixture.md) | FET HTML importer, L6 dataset, expected stats | FR-14 |
| 3 | [phase-03-workbook-io.md](phase-03-workbook-io.md) | Excel/CSV import/export contract | FR-2, FR-3, NFR-4 |
| 4 | [phase-04-solver-hard.md](phase-04-solver-hard.md) | CP-SAT solver, hard constraints, CLI | FR-8, FR-10, NFR-1, NFR-3 |
| 5 | [phase-05-preflight-explain.md](phase-05-preflight-explain.md) | Pre-flight checks + infeasibility explanation | FR-6, FR-8, NFR-7 |
| 6 | [phase-06-api-runs-worker.md](phase-06-api-runs-worker.md) | Persistence, REST API, runs, worker, exports | FR-7, FR-11, FR-13 |
| 7 | [phase-07-web-ui.md](phase-07-web-ui.md) | Table-first UI, Start panel, grids | FR-1, FR-7, FR-12, NFR-8 |
| 8 | [phase-08-soft-constraints.md](phase-08-soft-constraints.md) | Soft constraint catalogue, scoring | FR-9 |
| 9 | [phase-09-templates.md](phase-09-templates.md) | Templates → activities with preview | FR-5 |
| 10 | [phase-10-scale.md](phase-10-scale.md) | Multi-level/programme/university/building scale, staged solving | FR-15, NFR-2 |
| 11 | [phase-11-second-preset.md](phase-11-second-preset.md) | Exams preset with zero core changes | FR-16 |

The biggest technical risk is retired at the end of Phase 4, when L6 solves unpinned. Phases 5–11 are product work.
