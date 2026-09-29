# backend/CLAUDE.md

Python 3.12 · uv · FastAPI · SQLAlchemy 2 + Alembic · OR-Tools CP-SAT · Pydantic v2 · openpyxl · pytest + hypothesis.

## Package boundaries (enforced by `tests/unit/test_architecture.py`, same as `docs/spec/06-architecture.md` §3)

| Package | May import |
|---|---|
| `tts.core` | stdlib, pydantic only |
| `tts.expand`, `preflight` | `core` |
| `tts.solver` | `core`, ortools |
| `tts.io` | `core`, `presets` (sheet definitions only), openpyxl, bs4, jinja2 |
| `tts.presets.*` | `core` |
| `tts.store` | `core`, sqlalchemy |
| `tts.api`, `tts.worker`, `tts.cli` | any backend package |

`core.verifier` must never import `solver`.

## Rules
- Core models are frozen Pydantic v2 models. Core functions are pure.
- Each constraint type has two modules, both named after the type in `docs/spec/04-constraints.md`:
  - `core/constraints/<type>.py`: `Params` (a Pydantic model) and `verify(ds, result) -> list[Violation]`. No ortools.
  - `solver/constraints/<type>.py`: `compile(ctx, instance) -> None`, registered in `solver/registry.py`.

  A test asserts that every catalogue type has both modules.
- The solver pipeline stages are separate functions: `compile_model`, `solve`, `decode`, then `verify`. Don't merge them.
- Run the solver as `tts solve` or via the worker, never inside an API request.
- DB access goes only through `store/` repositories. Never use raw SQL outside `store/`, except for the `SKIP LOCKED` claim query in `worker/`.
- Change the schema only through Alembic migrations (`uv run alembic revision --autogenerate -m "..."`, then review the file by hand).

## Tests
- `unit/` is fast and pure. `property/` uses hypothesis to generate small datasets, solve them and check that the verifier finds no violations. `integration/` covers the API and DB (SQLite by default, Postgres when `TT_TEST_PG` is set). `scale/` holds the marked `scale` tests.
- Use the L6 fixture through `tests/fixtures/l6/conftest.py` fixtures (`l6_dataset`, `l6_locked_assignments`). Never mutate it in place.
