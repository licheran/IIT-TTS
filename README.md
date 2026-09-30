# IIT-TTS (IIT TimeTabling Solution)

**Conflict-free scheduling, driven by your spreadsheets.**

IIT-TTS is an open, data-driven scheduling application. You describe your world as tables of **resources** (people, groups, rooms, buildings), **events** (sessions to schedule) and **rules**. You edit them in the app or round-trip them through Excel/CSV, press **Start**, and IIT-TTS finds a timetable in which nothing is double-booked and your preferences are optimised.

The first built-in preset is **academic weekly timetabling**: lectures and tutorials for many levels, degree programmes and awarding universities, spread across several buildings and sharing teachers and rooms. The core engine is domain-neutral: a second preset, **exam timetabling**, runs on the same core with no changes to it. Staff rosters and room booking would be further presets, not rewrites.

> Status: **alpha. Every phase of the plan (0–11) is done:** the engine, the database and REST API with a background worker, the web app, the full soft-constraint catalogue, templates, institute-scale solving (about 3,000 events in under a minute) and the exams preset. See [`docs/STATUS.md`](docs/STATUS.md), including the decisions that are waiting for your review.

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
| Excel (`.xlsx`) and CSV (`.zip`) import and export | Works, in the app and on the command line. An import reads the whole workbook and reports every problem as `Sheet!R<row>C<col> [column]: message`. |
| Table editors | Works. One tab per sheet, inline editing with keyboard navigation, reference pickers, filter and sort; 5,000 rows scroll at 60 fps. |
| FET HTML import | Works (`tts import-fet`, `POST /validate`). |
| Templates | Works. Templates expand into activities, with a preview before committing. |
| Pre-flight checks | Works. Errors (for example a teacher needing more periods than they have) block a run. |
| Solve | Works: hard rules, and the 14 soft or hard constraint types of [spec 04](docs/spec/04-constraints.md) with a weighted score. L6 (77 events) solves in about 0.1 s, or scores 0 on the academic defaults in about 5 s; a synthetic institute of about 3,000 events solves in under a minute. |
| Staged solving and locks | Works (`tts solve --stage`, `stage_scope`). Published timetables of other datasets are respected on shared resources, and `tts clashes` / `GET /clashes` report conflicts between datasets. |
| Verify | Works. Every result is re-checked by an independent verifier. |
| Infeasibility explanations | Works. When no timetable exists, a minimal set of conflicting rules is named. |
| Runs | Works. Start, watch progress, cancel, publish, compare and re-run, in the app or through the API. |
| Grids and exports | Works. A weekly grid for any resource; HTML, Excel and CSV exports. |

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
| `tts clashes` | Finds clashes between the timetables of several workbooks |

The full reference, with every option and exit code, is in [`docs/cli.md`](docs/cli.md).

Git ignores files named `*.local.xlsx`, which keeps experiments out of commits.

See [`backend/README.md`](backend/README.md) for setup and how to run the tests.

The full stack runs with Docker:

```bash
docker compose up --build        # API on :8000, web app on :5173, PostgreSQL on :5432
bash scripts/smoke.sh            # import L6, solve it, fetch a grid and export it
```

Open http://localhost:5173, create a dataset, import a workbook (for example `backend/tests/fixtures/l6/l6.xlsx` or `backend/tests/fixtures/exams/exams.xlsx`), run pre-flight, press **Start** and open the timetable. The web app's own checks are `pnpm lint && pnpm typecheck && pnpm test && pnpm e2e` in `web/`.

## Developing with Claude Code

This repository is set up for [Claude Code](https://claude.com/claude-code):

- [`CLAUDE.md`](CLAUDE.md) holds the project rules, commands and workflow. There are extra guides in `backend/` and `web/`.
- `/next-task` picks up the next open task from the current phase, `/check` runs every quality gate, and `/new-adr` drafts a decision record.
- Progress is tracked in [`docs/STATUS.md`](docs/STATUS.md) and in the phase checklists.
