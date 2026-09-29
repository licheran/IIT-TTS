# Timetabler

**Conflict-free scheduling, driven by your spreadsheets.**

Timetabler is an open, data-driven scheduling application. You describe your world as tables of **resources** (people, groups, rooms, buildings), **events** (sessions to schedule) and **rules**. You edit them in the app or round-trip them through Excel/CSV, press **Start**, and Timetabler finds a timetable in which nothing is double-booked and your preferences are optimised.

The first built-in preset is **academic weekly timetabling**: lectures and tutorials for many levels, degree programmes and awarding universities, spread across several buildings and sharing teachers and rooms. The core engine is domain-neutral, so exams, staff rosters and room booking are future presets, not rewrites.

> Status: **pre-alpha, design complete, implementation starting.** See [`docs/STATUS.md`](docs/STATUS.md).

## How it works

```
Excel/CSV or table editor ──► Validate ──► Expand templates ──► Pre-flight checks
      ──► Solve (OR-Tools CP-SAT) ──► Verify ──► Grids + HTML/Excel/CSV exports
```

- **Declared vs assigned.** You declare who attends and teaches what, and what each session needs. The solver only assigns times and rooms.
- **Readable failures.** Pre-flight checks and infeasibility explanations tell you *which* rule or resource makes a timetable impossible.
- **Runs.** Every solve is saved with its inputs, so you can compare, publish, pin and re-run.

## Documentation

| Doc | Contents |
|---|---|
| [Product](docs/spec/01-product.md) | Definition, primary use case, requirements, non-goals |
| [Domain model](docs/spec/02-domain-model.md) | Core concepts, data model, selectors, academic mapping |
| [Workbook format](docs/spec/03-workbook-format.md) | The Excel/CSV import/export contract |
| [Constraints](docs/spec/04-constraints.md) | The constraint catalogue and its exact semantics |
| [Solver](docs/spec/05-solver.md) | CP-SAT formulation, pre-flight, explanations |
| [Architecture](docs/spec/06-architecture.md) | Packages, API, tech stack, quality gates |
| [Roadmap](docs/plan/ROADMAP.md) | Build phases and acceptance criteria |
| [ADRs](docs/adr/README.md) | Architecture decisions |

## Tech stack

Python 3.12 · FastAPI · OR-Tools CP-SAT · SQLAlchemy/Alembic · PostgreSQL · openpyxl · React + TypeScript · TanStack Table/Query · Tailwind · Docker Compose.

## Getting started

Implementation starts at [Phase 0](docs/plan/phase-00-setup.md). Once that is done:

```bash
docker compose up --build        # api :8000, web :5173, db :5432
```

## Developing with Claude Code

This repository is set up for [Claude Code](https://claude.com/claude-code):

- [`CLAUDE.md`](CLAUDE.md) holds the project rules, commands and workflow. There are extra guides in `backend/` and `web/`.
- `/next-task` picks up the next open task from the current phase, `/check` runs every quality gate, and `/new-adr` drafts a decision record.
- Progress is tracked in [`docs/STATUS.md`](docs/STATUS.md) and in the phase checklists.
