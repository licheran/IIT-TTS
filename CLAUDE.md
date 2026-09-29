# CLAUDE.md — Timetabler

Timetabler is a **generic, data-driven scheduling engine**. It places events in time and assigns them resources so that no exclusive resource is double-booked and all declared rules hold. The first preset is **academic weekly timetabling**: conflict-free course timetabling and room allocation for a multi-level, multi-programme, multi-university institute. That preset must be the easiest use case, but the core must not depend on it.

## Start every session here

1. Read `docs/STATUS.md`. It names the current phase and the next open task.
2. Read that phase file in `docs/plan/`, including its **Read first** list of spec files. Read only what is needed.
3. Work on **one task (checkbox) at a time**. Write the tests first where practical, then implement, then run the checks below.
4. When a task is done:
   - Tick its box in the phase file.
   - Add a line to the log in `docs/STATUS.md` (date, task, notes, follow-ups).
   - Commit with the message format below.
5. When every box in a phase is ticked and its **Acceptance** section passes, set the next phase as current in `docs/STATUS.md`.

**Stop and ask the user** when:
- a spec is ambiguous or contradicts another spec,
- a change would alter the workbook format, a spec or an ADR,
- a choice between real alternatives comes up (propose an ADR using `docs/adr/0000-template.md`),
- an acceptance criterion can't be met.

Don't loosen a test or an acceptance criterion to make it pass.

## Non-negotiable rules

1. **Core purity.** `core/`, `solver/`, `expand/` and `preflight/` must not contain domain words (`teacher`, `room`, `module`, `student`, `lecture`, `tutorial`, `group` as an academic term) and must not import `presets/`. Academic vocabulary lives only in `presets/academic_weekly/` and UI labels. A test enforces this.
2. **Independent verifier.** `core/verifier.py` never imports `solver/`. Every solver result is re-checked by the verifier, and tests assert on the verifier's output, not on solver status.
3. **Declared vs assigned.** The solver writes only `assignment` and `assigned_resource` rows inside a run. It never changes declared data.
4. **The workbook format is a contract** (`docs/spec/03-workbook-format.md`). Any change bumps `format_version`, updates that spec and adds a note to `docs/STATUS.md`.
5. **The L6 fixture stays green** (`backend/tests/fixtures/l6/`). Never edit `expected.json` to make a test pass unless the user approves.
6. **No invented real-world data.** Unknown values (group sizes, capacities) are assumptions, recorded in the fixture's `_meta` sheet.
7. **Fixed constraint catalogue.** New constraint behaviour means a new catalogue entry in `docs/spec/04-constraints.md` plus a module in `core/constraints/` (verify) and one in `solver/constraints/` (compile). Never add a special case inside the solver.
8. Never read or commit `.env` files or secrets.

## Commands

These are available once Phase 0 is done. Run them from the repository root unless stated otherwise.

```bash
# Backend (Python 3.12, uv)
cd backend && uv sync                      # install
uv run pytest                              # all tests
uv run pytest -m "not scale"               # fast tests (default for each task)
uv run ruff check . && uv run ruff format --check .
uv run mypy src                            # strict on src/timetabler/core
uv run timetabler solve <workbook.xlsx> --out result.xlsx --time-limit 60
uv run timetabler validate <workbook.xlsx> # verifier only

# Web (Node 20+, pnpm)
cd web && pnpm install
pnpm dev | pnpm test | pnpm lint | pnpm typecheck | pnpm e2e

# Everything
docker compose up --build
```

**Before marking any task done, run:** `uv run ruff check . && uv run mypy src && uv run pytest -m "not scale"`. Run the `pnpm` checks too if `web/` changed.

## Repository map

```
CLAUDE.md                 this file
docs/STATUS.md            current phase, progress log  ← read first
docs/spec/                what to build (authoritative)
  01-product.md             definition, use case, requirements (FR/NFR), non-goals
  02-domain-model.md        core concepts, tables, occupancy rule, selectors, academic mapping
  03-workbook-format.md     Excel/CSV import-export contract
  04-constraints.md         constraint catalogue with exact semantics
  05-solver.md              CP-SAT formulation, pre-flight, infeasibility explanation
  06-architecture.md        packages, dependency rules, API, stack, quality gates
docs/plan/                how to build it: ROADMAP.md + phase-NN-*.md
docs/adr/                 architecture decisions
backend/                  Python: src/timetabler/{core,expand,preflight,solver,io,presets,store,api,worker}
backend/tests/fixtures/l6/  real FET export (L6 SE+CS) + expected.json
web/                      React + TypeScript front end
.claude/commands/         /next-task, /check, /new-adr
```

## Conventions

- **Python:**
  - Type hints everywhere. Mypy runs strict on `core`.
  - Core models are frozen Pydantic v2 models, and core functions are pure (no I/O, no DB, no clock).
  - Errors are typed exceptions, never bare `Exception`.
- **Naming:**
  - Every entity has a string `code`. Relationships refer to codes in the workbook and to IDs in the database.
  - Time uses `day_index`, `period_index` and slot `t = day_index * P + period_index`.
- **Tests:**
  - `backend/tests/{unit,property,integration,scale}`. Mark slow tests `@pytest.mark.scale`.
  - Test names describe behaviour (`test_joint_event_occupies_all_child_groups`).
- **Commits:**
  - Conventional commits with a phase and task reference, for example `feat(core): add hierarchy occupancy [P1.2]`.
  - One task per commit where possible.
- **Docs:** if the code and the spec disagree, fix the code, or ask to change the spec. Never let them drift apart silently.
