# Status

**Current phase:** 28 Guided data entry ([phase-28-guided-entry.md](plan/phase-28-guided-entry.md)). Next task: **P28.1** (spec and ADR-0007 Amendment 3; stop and ask before code).

**Decisions waiting for you:** (1) Pins stay a table of hand-made datasets (P23.2); (2) ADR-0006 is still Proposed; (3) nothing is pushed yet, and GitHub CI has never run. The scale target (P20.8) is met since Phase 27: see [LOG.md](LOG.md). The three ADR-0007 proposals were confirmed on 2026-10-09.

**Where things are:** the progress log (one row per task, newest last) and the acceptance results of every phase are in [LOG.md](LOG.md). This file is read at the start of every session, so it stays short.

| Phase | State |
|---|---|
| 0 Setup | Done (the GitHub CI workflow has never been run) |
| 1 Core and verifier | Done |
| 2 L6 fixture | Done |
| 3 Workbook I/O | Done. **Open: open `l6.xlsx` in Excel or LibreOffice and check the dropdowns by hand** |
| 4 Solver v1 | Done |
| 5 Pre-flight and explanations | Done |
| 6 API, runs, worker | Done |
| 7 Web UI | Done |
| 8 Soft constraints | Done |
| 9 Templates | Done |
| 10 Scale | Done |
| 11 Exams preset | Done |
| 12 UI: quick entry, full HTML export | Done |
| 13 Wiki: tabs | Done |
| 14 Wiki: tables | Done |
| 15 Wiki: constraints and selectors | Done |
| 16 Wiki: troubleshooting | Done |
| 17 Wiki: exams preset | Done |
| 18 Configured sessions: specs and approval | Done |
| 19 Demands: core, verifier, pre-flight | Done |
| 20 Demands: solver | Done. The scale target was met in Phase 27 |
| 21 Academic configuration (format version 2) | Done |
| 22 Activities as the editable timetable | Done |
| 23 Retire Templates and ActivityGroups | Done |
| 24 The Session table (format version 2 amended) | Done |
| 25 Teacher fairness | Done (three new catalogue types, `Teachers.max_hours`, derived rules; ADR-0008) |
| 26 Reference drawer and a consistent UI | Done (ADR-0009, audit in `docs/plan/phase-26-audit.md`) |
| 27 Scale target for configured datasets | Done. Acceptance: the unchanged scale test passes (2,892 sessions, 8 workers: optimal in 76 s; NFR-2 15 min); closes P20.8 |
| 28 Guided data entry | **Current.** Hierarchy University → Programme → Level → Module (version 2 amended), tables in fill order, field help, time/date pickers |

**Format version:** workbook `format_version` 1 (hand-made datasets, exams) and 2 (configured academic datasets; amended by Phase 24)

## Pinned versions
Recorded 2026-09-29 (P0.8, backend part). The exact pins live in `backend/pyproject.toml` and `backend/uv.lock`.

| Area | Versions |
|---|---|
| Toolchain | Python 3.12.10 (`>=3.12`), uv 0.12.20, Node 24.18.0, pnpm 12.6.0, Docker 29.8.1 |
| Backend runtime | ortools 9.15.6755, pydantic 2.13.5, fastapi 0.141.1, uvicorn 0.54.0, sqlalchemy 2.1.1, alembic 1.20.0, psycopg 3.3.6, openpyxl 3.1.5, pandas 3.0.6, jinja2 3.1.6, beautifulsoup4 4.15.0, typer 0.27.2 |
| Backend dev | pytest 9.1.1, hypothesis 6.168.3, ruff 0.16.9, mypy 2.3.1, httpx 0.28.1, import-linter 2.15 |
| Web | @tanstack/react-query 5.104.0, @tanstack/react-table 8.21.3, @tanstack/react-virtual 3.14.13, class-variance-authority 0.7.1, clsx 2.1.1, openapi-fetch 0.17.0, react 19.3.0, react-dom 19.3.0, react-router-dom 7.18.4, tailwind-merge 3.7.0, @eslint/js 10.0.1, @playwright/test 1.63.0, @tailwindcss/vite 4.3.3, @testing-library/jest-dom 7.0.1, @testing-library/react 16.3.3, @testing-library/user-event 14.6.7, @types/node 26.6.3, @types/react 19.3.0, @types/react-dom 19.3.0, @vitejs/plugin-react 6.1.1, eslint 10.11.0, eslint-plugin-react-hooks 7.1.1, globals 17.12.0, jsdom 30.1.1, openapi-typescript 7.13.0, prettier 3.9.9, tailwindcss 4.3.3, typescript 6.0.3, typescript-eslint 8.71.0, vite 8.3.1, vitest 5.0.2 (exact pins in `web/package.json`; TypeScript is 6.0 because `openapi-typescript` needs the JS compiler API, which TypeScript 7 lacks) |

## Answered questions
Answered by the user on 2026-09-30.
- **Group sizes and room capacities.** Real group sizes are 20–60 students and room capacities 30–120, but both must be configurable to any number. The largest room is a hard limit: a group or joint event that does not fit in any room is infeasible (already H3, and pre-flight `no_candidate`). The fixture assumptions (30 per group, derived room sizes) stay assumptions.
- **Teacher codes.** A teacher has exactly one code, and a code refers to exactly one teacher, unique across universities. No aliasing or merging is needed.
- **Teaching days and block lengths.** Universities and levels may use different teaching days or block lengths. The model already allows it through start patterns and availability, but the workbook format has no per-university or per-level pattern yet (Phase 10: check that events, patterns and availability can express it, or propose a format change).
- **Travel between buildings.** No free period is needed for a building change. The default `AC-TRAVEL` (`travel_gap`, spec 04 §3) is therefore **not enabled by default** (P8.3). The `travel_gap` type stays in the catalogue.
- **Scope.** One institute-wide dataset, so no staged-by-level workflow is required. Staged solving (P10.2) stays as a scaling tool only.
- **Repository.** Public. The FET export in the fixture is old and deprecated, and its teacher codes are examples only, so nothing sensitive is committed. `l6.xlsx` may be committed.

## Open questions (need answers from the user)
None about ADR-0007: its three proposals (even split 3 + 3 + 2 + 2, one optional flag per module, an edit waits for Rebuild) were confirmed on 2026-10-09.

Answered on 2026-09-30 (ADR-0007):
- the design is approved, and "demand" is the core name;
- the solver decides which groups share a session; the user sets the number of groups per session, so the number of sessions is fixed (no "fewer sessions" rule); the room must seat all their students;
- a group keeps the same companions every time its session repeats in the week;
- session types are configured by the user;
- a degree has levels, a level has modules; each module has exactly one level and a mandatory/optional field; a group is students with the same optional modules and lists them in `options`;
- a group's parent is always a programme: no subgroups (in format version 2);
- ActivityTeachers and Pins go too;
- any manual edit to the timetable makes the next run a complete rebuild that keeps the edited values; no partial repair, no lock marks to manage;
- the timetable and the edits are not part of the workbook: the workbook is configuration only;
- teacher fairness is the last phase (24).

## Log

The progress log and the acceptance results of every phase are in [LOG.md](LOG.md). Add new entries there (rule 4 format-change notes too).
