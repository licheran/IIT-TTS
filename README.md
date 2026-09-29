# IIT-TTS (IIT TimeTabling Solution)

**Conflict-free scheduling, driven by your spreadsheets.**

IIT-TTS is an open, data-driven scheduling application. You describe your world as tables of **resources** (people, groups, rooms, buildings), **events** (sessions to schedule) and **rules**. You edit them in the app or round-trip them through Excel/CSV, press **Start**, and IIT-TTS finds a timetable in which nothing is double-booked and your preferences are optimised.

The first built-in preset is **academic weekly timetabling**: lectures and tutorials for many levels, degree programmes and awarding universities, spread across several buildings and sharing teachers and rooms. The core engine is domain-neutral, so exams, staff rosters and room booking are future presets, not rewrites.

> Status: **pre-alpha. The backend engine works from the command line; there is no web app yet.** Phases 1–4 are done: the core model and verifier, the L6 regression fixture, Excel/CSV import and export, and the CP-SAT solver for the hard rules. Phase 5 (pre-flight checks and infeasibility explanations) is under way: the pre-flight checks work, the explanations are next. See [`docs/STATUS.md`](docs/STATUS.md).

## How it works

```
Excel/CSV or table editor ──► Validate ──► Expand templates ──► Pre-flight checks
      ──► Solve (OR-Tools CP-SAT) ──► Verify ──► Grids + HTML/Excel/CSV exports
```

- **Declared vs assigned.** You declare who attends and teaches what, and what each session needs. The solver only assigns times and rooms.
- **Independent verifier.** Every result the solver returns is checked again by a separate verifier, which never uses solver code.
- **Readable failures.** Pre-flight checks and infeasibility explanations tell you *which* rule or resource makes a timetable impossible.
- **Runs.** Every solve is saved with its inputs, so you can compare, publish, pin and re-run.

### What works today

| Step | State |
|---|---|
| Excel (`.xlsx`) and CSV (`.zip`) import and export | Works. Import reads the whole workbook and reports every problem as `Sheet!R<row>C<col> [column]: message`. |
| FET HTML import | Works (`tts import-fet`). |
| Validate | Works. Checks the data and the hard rules. |
| Solve | Works for the hard rules: no double-booking, availability, room capacity and type, pins. The real L6 timetable (77 events) solves in about 0.1 s. |
| Verify | Works. Runs after every solve. |
| Declared constraints (the catalogue in [spec 04](docs/spec/04-constraints.md)) | Phase 8. `tts solve` refuses a workbook that declares a hard one, and warns about a soft one. |
| Expand templates | Phase 9. |
| Pre-flight checks | Works (`tts preflight`, and before every `tts solve`). Errors such as a resource needing more periods than it has stop the solve with exit code 4. |
| Infeasibility explanations | Phase 5 (in progress): "which rules conflict" when the solver proves there is no timetable. |
| Saved runs, API, web app, grids, HTML export | Phases 6–7. |

## Documentation

| Doc | Contents |
|---|---|
| [Product](docs/spec/01-product.md) | Definition, primary use case, requirements, non-goals |
| [Domain model](docs/spec/02-domain-model.md) | Core concepts, data model, selectors, academic mapping |
| [Workbook format](docs/spec/03-workbook-format.md) | The Excel/CSV import/export contract |
| [Constraints](docs/spec/04-constraints.md) | The constraint catalogue and its exact semantics |
| [Solver](docs/spec/05-solver.md) | CP-SAT formulation, pre-flight, explanations |
| [Architecture](docs/spec/06-architecture.md) | Packages, API, tech stack, quality gates |
| [Command line](docs/cli.md) | Every `tts` command, option, output and exit code |
| [Roadmap](docs/plan/ROADMAP.md) | Build phases and acceptance criteria |
| [ADRs](docs/adr/README.md) | Architecture decisions |

## Tech stack

Python 3.12 · FastAPI · OR-Tools CP-SAT · SQLAlchemy/Alembic · PostgreSQL · openpyxl · React + TypeScript · TanStack Table/Query · Tailwind · Docker Compose.

## Getting started

You need Python 3.12 and [uv](https://docs.astral.sh/uv/). Everything below runs in `backend/`:

```bash
cd backend
uv sync                                    # install

# Turn the L6 FET export into a workbook, then solve it
uv run tts import-fet tests/fixtures/l6/fet-groups-export.html --out l6.local.xlsx
uv run tts preflight l6.local.xlsx         # quick checks, no solving
uv run tts solve l6.local.xlsx --out l6-solved.local.xlsx --time-limit 30
uv run tts validate l6-solved.local.xlsx   # check a workbook's Assignments
```

| Command | What it does |
|---|---|
| `tts import-fet` | Converts a FET HTML export into a workbook |
| `tts export` | Rewrites a workbook in canonical form, or converts Excel ↔ CSV |
| `tts preflight` | Finds what makes a timetable impossible, without solving |
| `tts solve` | Pre-flight, solve, verify, and write the timetable back |
| `tts validate` | Checks a workbook's assignments with the independent verifier |

The full reference, with every option and exit code, is in [`docs/cli.md`](docs/cli.md).

Git ignores files named `*.local.xlsx`. The L6 workbooks contain real teacher codes, so keep them out of commits.

See [`backend/README.md`](backend/README.md) for setup and how to run the tests.

The full stack (API, worker, database and web app) is meant to run with `docker compose up --build`, serving the API on :8000, the web app on :5173 and the database on :5432. That command is not ready yet: the web app has not been scaffolded ([Phase 0](docs/plan/phase-00-setup.md), task P0.5).

## Developing with Claude Code

This repository is set up for [Claude Code](https://claude.com/claude-code):

- [`CLAUDE.md`](CLAUDE.md) holds the project rules, commands and workflow. There are extra guides in `backend/` and `web/`.
- `/next-task` picks up the next open task from the current phase, `/check` runs every quality gate, and `/new-adr` drafts a decision record.
- Progress is tracked in [`docs/STATUS.md`](docs/STATUS.md) and in the phase checklists.
