# IIT-TTS backend (`tts`)

The scheduling engine: the domain-neutral core, the independent verifier, workbook import and export, and the OR-Tools CP-SAT solver, all driven by the `tts` command. Project rules are in [`CLAUDE.md`](CLAUDE.md). The specs are in [`../docs/spec/`](../docs/spec/).

## Setup

You need Python 3.12 and [uv](https://docs.astral.sh/uv/). Dependencies are pinned exactly in `pyproject.toml` and `uv.lock`.

```bash
uv sync
```

## The `tts` command

Run `uv run tts --help`, or `uv run tts <command> --help` for one command.

Workbooks are either `.xlsx` or CSV `.zip` files; the file extension decides which. Both follow the contract in [spec 03](../docs/spec/03-workbook-format.md). Reading a workbook is all or nothing: if anything is wrong, every problem is listed as `Sheet!R<row>C<col> [column]: message` and nothing is used.

| Command | What it does | Exit codes |
|---|---|---|
| `tts solve <workbook> --out <file> [--time-limit S] [--workers N] [--seed K]` | Solves the workbook, checks the result with the verifier, and writes it back with an `Assignments` sheet. Assignments already in the workbook are ignored and solved again. With `--workers 1` and a fixed `--seed`, the same input always gives the same result. | 0 written · 1 the workbook could not be read, or it uses a constraint type the solver does not support yet · 2 no timetable exists, or none was found within the time limit · 3 the solver's result broke a hard rule (a bug), so nothing was written |
| `tts validate <workbook>` | Runs the verifier on the workbook's `Assignments` and lists every violation. | 0 no hard violation · 1 the workbook could not be read, or has no assignments · 3 at least one hard violation |
| `tts import-fet <export.html> --out <file> [--with-assignments]` | Converts a FET "groups" HTML export into a workbook (`.xlsx` or `.zip`) or into JSON (`.json`). Values the export does not contain, such as group sizes and room capacities, are assumptions and are written to `_meta`. `--with-assignments` also writes the export's own placements. | 0 written · 1 the export could not be read |
| `tts export <input> --out <file> [--with-assignments]` | Rewrites a workbook in canonical form, in either format. It also turns an `import-fet` `.json` into a workbook. | 0 written · 1 the input has problems |

Every command exits with 2 on a usage error, such as a missing input file or an unrecognised file extension.

Example, using the L6 regression fixture:

```bash
uv run tts import-fet tests/fixtures/l6/fet-groups-export.html --out l6.local.xlsx
uv run tts solve l6.local.xlsx --out l6-solved.local.xlsx --time-limit 30
```

The generated workbooks contain real teacher codes. Git ignores files named `*.local.xlsx`; see the fixture's [README](tests/fixtures/l6/README.md#privacy).

The API (`tts.api`) exposes only `GET /health` so far, and the worker (`tts.worker`) is a stub. Both arrive in Phase 6.

## Layout

| Package | Contents |
|---|---|
| `tts.core` | Frozen Pydantic models, the hierarchy (the occupancy rule), the time grid, selectors, sheet definitions, the constraint catalogue and the verifier. Pure and domain-neutral. |
| `tts.solver` | Builds the CP-SAT model (`compile_model`), solves it and decodes the result. |
| `tts.io` | Workbook `.xlsx` and CSV `.zip` import and export, and FET HTML import. |
| `tts.presets.academic_weekly` | The academic preset: resource types, sheets and labels. The only place with academic vocabulary. |
| `tts.expand`, `tts.preflight`, `tts.store` | Empty; filled in by later phases. |
| `tts.cli`, `tts.api`, `tts.worker` | Entry points. |

Allowed imports between packages are listed in [`CLAUDE.md`](CLAUDE.md) and enforced by `tests/unit/test_architecture.py`. The same test checks that `core`, `solver`, `expand` and `preflight` contain no academic vocabulary.

## Checks

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy src                 # strict on tts.core
uv run pytest -m "not scale"    # fast suite: unit, property, integration, L6 fixture
uv run pytest -m scale          # slow scale tests (the nightly CI job runs these)
uv run pytest -k l6             # only the L6 regression tests
```

Tests judge every solver result by the verifier's output, not by the solver's status.
