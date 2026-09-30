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
| 12 | [phase-12-ui-quick-entry.md](phase-12-ui-quick-entry.md) | Always-visible entry row (Tab/Enter); every timetable in one HTML file | FR-1, FR-13 |
| 13 | [phase-13-wiki-tabs.md](phase-13-wiki-tabs.md) | User wiki: skeleton and every tab | — |
| 14 | [phase-14-wiki-tables.md](phase-14-wiki-tables.md) | Wiki: every table of the academic preset, and tags | — |
| 15 | [phase-15-wiki-constraints.md](phase-15-wiki-constraints.md) | Wiki: constraint types and the selector language | — |
| 16 | [phase-16-wiki-troubleshooting.md](phase-16-wiki-troubleshooting.md) | Wiki: every error, issue and run status, with fixes | — |
| 17 | [phase-17-wiki-exams.md](phase-17-wiki-exams.md) | Wiki: the exams preset's tables | — |
| 18 | [phase-18-sessions-design.md](phase-18-sessions-design.md) | Configured sessions: ADR-0007 approved, specs updated | FR-17–FR-20 (new) |
| 19 | [phase-19-demands-core.md](phase-19-demands-core.md) | Demands in the core, verifier (H6) and pre-flight | FR-18, FR-14 |
| 20 | [phase-20-demands-solver.md](phase-20-demands-solver.md) | The solver splits demands into sessions and picks teachers | FR-18, FR-8 |
| 21 | [phase-21-academic-configuration.md](phase-21-academic-configuration.md) | Session types, module sessions, teacher modules, programme and group modules (format version 2) | FR-17, FR-2 |
| 22 | [phase-22-editable-timetable.md](phase-22-editable-timetable.md) | Activities as the editable timetable; edited fields are kept | FR-19, FR-10 |
| 23 | [phase-23-retire-templates.md](phase-23-retire-templates.md) | Templates, ActivityGroups, ActivityTeachers and Pins retired from the academic preset | FR-17 |
| 24 | [phase-24-teacher-fairness.md](phase-24-teacher-fairness.md) | Teacher workload cap, balance and continuity | FR-20 |

The biggest technical risk is retired at the end of Phase 4, when L6 solves unpinned. Phases 5–11 are product work. Phase 12 is a UI refinement. Phases 13–17 are documentation: the user wiki in `docs/wiki/`, kept in step with the code by `backend/tests/unit/test_wiki.py`. Phases 18–24 build timetables from configuration (ADR-0007): the new risk is solve time once the solver decides which groups share a session, measured in P20.8.
